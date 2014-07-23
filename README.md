# watchgit

####Table of Contents

1. [Overview - _What it is_](#overview)
2. [Description - _What it does_](#description)
3. [Setup - _How to set it up_](#setup)
    * [Requirements](#requirements)
    * [Installation](#installation)
4. [Usage - _How to use it_](#usage)
    * [watchgit.py - _daemon_](#watchgitpy)
    * [watchgit.conf - _configuration file_](#watchgitconf)

## Overview
Keep local git repositories in sync

## Description
Watchgit is a daemon that keeps local git repositories in sync. It does this by periodically pulling a remote for every repository specified in its configuration file.

* Monitors repositories specified in [watchgit.conf](#watchgitconf)
* Periodically pulls a ref specified by [ref](#watchgitconf) and [interval](#watchgitconf) from a [remote](#watchgitconf)
* Clones the repository if it does not exist.

## Setup

### Requirements
* Python 2.7
* [python-daemon](https://pypi.python.org/pypi/python-daemon/1.6) (>=1.6)
* [GitPython](http://pythonhosted.org/GitPython/0.3.2/) (>= 0.3.1)

### Installation
#### Setuptools
    python setup.py install

#### RPM
(**TODO** - files can be found under [ext/redhat](ext/redhat))

## Usage

### watchgit.py

    usage: watchgit.py [-h] [-c CONFIG] [-p PIDFILE] [-f] command

    positional arguments:
      command               [start|stop|status]

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG, --config CONFIG
                            configuration file. (Default: watchgit.conf)
      -p PIDFILE, --pidfile PIDFILE
                            pid file. (Default: watchgit.pid)
      -f, --foreground      run in foreground

### watchgit.conf
Global defaults and parameters such as logfile and loglevel are specified under the `GLOBAL` section.

    [GLOBAL]
    interval      = 5
    ref           = master
    reset         = true
    logfile       = watchgit.log
    loglevel      = info
    skip_on_error = false
    user          = nobody
    group         = nogroup


Individual repositories are specified as their own section with the name of the repository as the section name.

    [watchgit]
    interval      = 300
    local         = /opt/watchgit/
    remote        = https://github.com/tdevelioglu/watchgit.git
    reset         = false
    skip_on_error = true
    user          = someuser
    group         = somegroup

#### Global parameters

* `interval` - How frequently to pull a repository's remote.
* `ref` - Remote ref to use when pulling.
* `reset` - Whether to reset the local HEAD before pulling.
* `logfile` - Location of the logfile.
* `loglevel` - Log level.
* `skip_on_error` - Whether to skip repositories if an error occurs during clone or open.
* `user` - User to run the watchgit daemon as.
* `group` - Group to run the watchgit daemon as.

#### Repo parameters
* `interval` - How frequently to pull the repository's remote.
* `local` - Local filesystem path to the repository.
* `remote` - Url to the remote repository.
* `ref` - Remote ref to use when pulling.
* `reset` - Whether to reset the local HEAD before pulling.
* `skip_on_error` - Whether to skip the repository if an error occurs during clone or open.
* `user` - User to watch the repository as.
* `group` - Group to watch the repository as.

