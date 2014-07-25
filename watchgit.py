#!/usr/bin/python

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# @author: Taylan Develioglu <taylan.develioglu@gmail.com>

import ConfigParser
import daemon
import logging, logging.handlers
import multiprocessing
import os
import sys
import time
import traceback
from argparse import ArgumentParser
from git import Repo
from grp import getgrgid, getgrnam
from lockfile.pidlockfile import PIDLockFile
from pwd import getpwnam

class Watcher(multiprocessing.Process):
    def __init__(self, name, config, daemon=None):
        self.config   = config

        if os.getuid() == 0:
            self.uid = getpwnam(self.config.get(name, 'user')).pw_uid
            self.gid = getgrnam(self.config.get(name, 'group')).gr_gid
        else:
            self.uid = os.getuid()
            self.gid = os.getgid()

        self.all_remotes   = config.getboolean(name, 'all_remotes')
        self.local         = config.get(name, 'local')
        self.remote        = config.get(name, 'remote')
        self.ref           = config.get(name, 'ref')
        self.interval      = config.getfloat(name, 'interval')
        self.reset         = config.getboolean(name, 'reset')
        self.skip_on_error = config.getboolean(name, 'skip_on_error')
        self.user          = config.get(name, 'user')
        self.group         = config.get(name, 'group')

        super(Watcher, self).__init__(name=name)

        if daemon is not None:
            self.daemon = daemon
        self.start()

    def run(self):
        os.seteuid(0)
        os.setgid(self.gid)
        os.setuid(self.uid)

        # In case of nonexistent path or empty directory clone the repository.
        # Otherwise open it.
        try:
            if not os.path.exists(self.local) or not os.listdir(self.local):
                os.umask(0022)
                logger.info("Cloning repo '%s' from '%s' to '%s'" % (self.name, self.remote, self.local))
                repo = Repo.clone_from(self.remote, self.local)
            else:
                logger.info("Loading repo '%s' at '%s'" % (self.name, self.local))
                repo = Repo(self.local)

            # To make sure our remote is up to date, we delete and create it 
            # again.
            if 'watchgit' in [remote.name for remote in repo.remotes]:
                logger.debug("Deleting remote 'watchgit' from repository '%s'" % self.name)
                repo.delete_remote('watchgit')

            logger.debug("Creating remote '%s' on repository '%s'" % (self.remote, self.name))
            remotes = [repo.create_remote('watchgit', self.remote)]
            
            # if all_remotes is set we pull from all remotes
            if self.all_remotes is True:
                remotes = repo.remotes

        # If skip_on_error is true, we don't need to raise a fatal exception.
        # Instead we signal our watcher with the exitcode that we failed while
        # trying to load the repo.
        except Exception as e:
            if self.skip_on_error is True:
                logger.warn(e, exc_info=1)
                os._exit(128)
            else:
                raise

        # Start the watch
        logger.info("Starting watch of repository at '%s'" % repo.working_dir)
        while True:
            logger.debug("Pulling ref '%s' for '%s'" % (self.ref, repo.working_dir))
            if self.reset is True and repo.is_dirty():
                logger.info("Resetting dirty repository at '%s'" % repo.working_dir)
                repo.head.reset(working_tree=True)
            for remote in remotes:
                logger.debug("Pulling remote '%s'", remote.name)
                remote.pull(self.ref)

            time.sleep(self.interval)

###########################################################################
# Parent watcher class
###########################################################################
class WatchGit(object):
    def __init__(self, config):
        self.config = config

        if os.getuid() == 0:
            self.uid = getpwnam(self.config.get('GLOBAL', 'user')).pw_uid
            self.gid = getgrnam(self.config.get('GLOBAL', 'group')).gr_gid
        else:
            self.uid = os.getuid()
            self.gid = os.getgid()

    def run(self):
        # Drop privileges
        os.seteuid(0)
        os.setegid(self.gid)
        os.seteuid(self.uid)

        children = []
        for section in [s for s in self.config.sections() if s != 'GLOBAL']:
            logger.debug("Launching watcher for repository '%s'" % section)
            children.append(Watcher(section, config, True))

        # Watch our children. If one dies, respawn it.
        while True:
            logger.debug('Checking the health of %d children' % len(children))

            # Delete children set to None, e.g. when an error occurs during a
            # child's initialization below.
            children = filter(lambda c: c is not None, children)

            # Check every child if it's still alive, respawn it if it isn't.
            for idx, child in enumerate(children):
                logger.debug("Checking if child '%s' is still alive..." % child.name)
                if not child.is_alive():
                    # If a child exits with exitcode 128, something went wrong
                    # during initialization of the repo. (load or clone) and
                    # skip_on_error was set.
                    # It means we can simply skip watching this repo.
                    if child.exitcode == 128:
                        logger.warn("Error while initializing repo '%s' - Skipping" % child.name)
                        children[idx] = None
                        continue

                    logger.warn(('Child (%s) with pid %s (exitcode: %s) ' +
                            'died.') % (child.name, child.pid,
                                                    child.exitcode))
                     # respawn watcher
                    logger.warn("Restarting watch of repository '%s'" % child.name)
                    children[idx] = Watcher(child.name, child.config, True)

            # Arbitrary time interval to sleep before starting a new round of
            # checks.
            time.sleep(1)

    def stop(self):
        os.seteuid(0)
        sys.exit()

class GentleConfigParser(ConfigParser.RawConfigParser):
    def get(self, section, option, default=None):
        try:
            return ConfigParser.RawConfigParser.get(self, section, option)
        except ConfigParser.NoOptionError:
            return default
        except:
            raise

def running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

###########################################################################
# Main
###########################################################################
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-c', '--config',
        help='configuration file. (Default: watchgit.conf)',
        default=os.path.realpath('watchgit.conf'))
    parser.add_argument('-p', '--pidfile',
        help='pid file. (Default: watchgit.pid)',
        default=os.path.realpath('watchgit.pid'))
    parser.add_argument('-f', '--foreground', help='run in foreground',
        action='store_true')
    parser.add_argument('command', help='[start|stop|status]')
    args = parser.parse_args()

    if args.command == 'start':
        # Init config
        defaults = {
            'all_remotes'      : 'false',
            'interval'         : 5,
            'logfile'          : 'watchgit.log',
            'loglevel'         : 'INFO',
            'ref'              : 'master',
            'reset'            : 'true',
            'user'             : 'nobody',
            'skip_on_error'    : 'false',
        }

        config = GentleConfigParser()
        config.read(args.config)

        # Determining a default group depends on the osfamily.
        # 1) 'nogroup' (Debian based systems)
        # 2) 'nobody'  (Redhat based systems)
        try:
            group = getgrnam('nogroup').gr_name
        except KeyError:
            group = getgrnam('nobody').gr_name
        config.defaults()['group'] = group

        # Populate defaults from GLOBAL section or fall back to defaults above
        for k,v in defaults.iteritems():
            config.defaults()[k] = config.get('GLOBAL', k, v)

        logfile  = config.get('GLOBAL', 'logfile')
        loglevel = config.get('GLOBAL', 'loglevel').upper()

        # Set up logger and exception hook
        logger = multiprocessing.get_logger()
        logger.setLevel(getattr(logging , loglevel))
        if args.foreground is True:
            fh = logging.StreamHandler()
        else:
            fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=(10*1024*1024),
                backupCount=9)

            def excepthook(ex_cls, ex, tb):
                logger.error('Traceback (most recent call last)')
                logger.error(''.join(traceback.format_tb(tb)))
                logger.error('{0}: {1}'.format(ex_cls, ex))
            sys.excepthook = excepthook

        fh.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)

        pidfile = PIDLockFile(args.pidfile)
        logger.info('Launching watchgit daemon')
        watchgit = WatchGit(config)
        if args.foreground is True:
            watchgit.run()
        else:
            with daemon.DaemonContext(files_preserve=[fh.stream],
                    signal_map={15: lambda signum, frame: watchgit.stop()},
                    pidfile=pidfile):
                watchgit.run()

    if args.command == 'stop':
        if os.path.exists(args.pidfile):
            pid = int(open(args.pidfile).read().rstrip())
            # Check if process is running
            if running(pid):
                print 'Stopping watchgit (pid %s)' % pid
                os.kill(pid, 15)

                for x in xrange(10):
                    if not running(pid):
                        break
                    time.sleep(0.5)
            else:
                print 'No running process (%s) found. Cleaning up pidfile' % pid
                os.unlink(args.pidfile)
                exit(0)
        else:
            print '%s not found.' % args.pidfile

    if args.command == 'status':
        if os.path.exists(args.pidfile):
            pid = int(open(args.pidfile).read().rstrip())
            # Check if process is running
            if running(pid):
                print 'watchgit (pid %s) is running...' % pid
            else:
                print 'No running process (%s) found. Cleaning up pidfile' % pid
                os.unlink(pidfile)
                exit(1)
        else:
            print '%s not found.' % args.pidfile
            exit(1)

