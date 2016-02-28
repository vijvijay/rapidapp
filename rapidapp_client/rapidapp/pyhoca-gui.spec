Name:           pyhoca-gui
Version:        0.5.0.0
Release:        0.0x2go1%{?dist}
Summary:        Graphical X2Go client written in (wx)Python

Group:          Applications/Communications
%if 0%{?suse_version}
License:        AGPL-3.0+
%else
License:        AGPLv3+
%endif
URL:            http://www.x2go.org/
Source0:        http://code.x2go.org/releases/source/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch
%if 0%{?suse_version}
BuildRequires:  python-devel
BuildRequires:  fdupes
%else
BuildRequires:  python2-devel
%endif
BuildRequires:  python-setuptools
BuildRequires:  python-distutils-extra
BuildRequires:  desktop-file-utils
BuildRequires:  intltool
Requires:       python-setproctitle
Requires:       python-x2go >= 0.5.0.0
%if 0%{?suse_version}
Requires:       python-notify
%else
Requires:       notify-python
%endif
%if 0%{?suse_version} >= 1230
Requires:       python-wxWidgets-2_9
%else
Requires:       wxPython
%endif
Requires:       python-argparse
Requires:       python-cups

%description
X2Go is a server based computing environment with:
   - session resuming
   - low bandwidth support
   - LDAP support
   - client side mass storage mounting support
   - client side printing support
   - audio support
   - authentication by smartcard and USB stick

PyHoca-GUI is a slim X2Go client that docks to the desktop's
notification area and allows multiple X2Go session handling.


%prep
%setup -q


%build
%{__python} setup.py build_i18n
%{__python} setup.py build


%install
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p %{buildroot}%{_bindir}/
cp -p %{name} %{buildroot}%{_bindir}/
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop
%if 0%{?fdupes:1}
%fdupes %buildroot/%_prefix
%endif


%post
/bin/touch --no-create %{_datadir}/icons/PyHoca &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/PyHoca &>/dev/null
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/PyHoca &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/PyHoca &>/dev/null || :


%files
%defattr(-,root,root)
%doc COPYING README TODO
%{_bindir}/%{name}
%{python_sitelib}/*
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/PyHoca/
%{_datadir}/pixmaps/pyhoca_x2go-logo-ubuntu.svg
%{_datadir}/pyhoca
%{_mandir}/man1/%{name}.1*
%{_datadir}/locale

%changelog
