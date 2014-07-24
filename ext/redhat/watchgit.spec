%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%global _with_systemd 1
%else
%global _with_systemd 0
%endif

%global confdir ext/redhat
%global realname watchgit

Summary:       Keep local git repositories in sync
Name:          watchgit
Version:       0.2.0
Release:       1%{?dist}
Source0:       https://github.com/tdevelioglu/watchgit/archive/%{version}.tar.gz
License:       ASL 2.0
Group:         System Environment/Daemons
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch:     noarch
BuildRequires: python
BuildRequires: python-setuptools
Requires:      python-daemon
Requires:      python-GitPython

# Redhat-friendly config file patch
Patch1: conffile.patch

%description
Keep local git repositories in sync

%prep
%setup -n %{realname}-%{version}
%patch1 -p1

%build
python setup.py build

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
install -D -m 0755 watchgit.py %{buildroot}%{_sbindir}/watchgit
install -D -m 0755 %{confdir}/init %{buildroot}/%{_initrddir}/watchgit
install -D -m 0644 %{confdir}/sysconfig %{buildroot}/%{_sysconfdir}/sysconfig/watchgit
install -D -m 0644 watchgit.conf %{buildroot}%{_sysconfdir}/watchgit.conf
install -d -m 0755 %{buildroot}%{_localstatedir}/log/watchgit

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%ghost %{_bindir}/watchgit.py
%{_sbindir}/watchgit
%{_initrddir}/watchgit
%config(noreplace) %{_sysconfdir}/watchgit.conf
%config(noreplace) %{_sysconfdir}/sysconfig/watchgit
%defattr(-, watchgit, watchgit, 0755)
%dir %attr(0755, root, root) %{_localstatedir}/log/watchgit

%pre
getent passwd watchgit &>/dev/null || \
useradd -r -s /sbin/nologin -d %{_localstatedir}/run/watchgit -C "Watchgit" watchgit &>/dev/null

%post
if [ "$1" -ge 1 ]; then
%if 0%{?_with_systemd}
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    /bin/systemctl start watchgit.service) >/dev/null 2>&1 || :
%else
    /sbin/chkconfig --add watchgit || :
    /sbin/service watchgit start) >/dev/null 2>&1 || :
%endif
fi

%preun
if [ "$1" -eq 0 ] ; then
%if 0%{?_with_systemd}
    /bin/systemctl --no-reload disable watchgit.service > /dev/null 2>&1 || :
    /bin/systemctl stop watchgit.service > /dev/null 2>&1 || :
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
%else
    /sbin/service watchgit stop > /dev/null 2>&1
    /sbin/chkconfig --del watchgit || :
%endif
fi

%changelog
* Wed Jul 23 2014 Taylan Develioglu <taylan.develioglu@booking.com> -  0.2.0-1
- Bump to 0.2.0
