#if 0%{?fedora}
#global with_python3 1
#endif

Name:           python-x2go
Version:        0.5.0.1
Release:        0.0x2go1%{?dist}
Summary:        Python module providing X2Go client API

Group:          Development/Languages
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
%if 0%{?with_python3}
BuildRequires:  python3-devel
# For 2to3
BuildRequires:  python-tools
%endif # if with_python3
# For doc build
BuildRequires:  epydoc
BuildRequires:  python-gevent
BuildRequires:  python-paramiko
BuildRequires:  python-xlib
BuildRequires:  python-requests
BuildRequires:  python-simplejson
Requires:       nxproxy
Requires:       python-gevent
Requires:       python-paramiko >= 1.15.1
Requires:       python-xlib
Requires:       python-requests
Requires:       python-simplejson

%description
X2Go is a server based computing environment with:
   - session resuming
   - low bandwidth support
   - session brokerage support
   - client side mass storage mounting support
   - audio support
   - authentication by smartcard and USB stick

This Python module allows you to integrate X2Go client support into your
Python applications by providing a Python-based X2Go client API.


%package        doc
Summary:        Python X2Go client API documentation
Group:          Documentation
Requires:       %{name} = %{version}-%{release}

%description    doc
This package contains the Python X2Go client API documentation.


%if 0%{?with_python3}
%package -n python3-x2go
Summary:        Python module providing X2Go client API
Group:          Development/Languages

%description -n python3-x2go
X2Go is a server based computing environment with:
   - session resuming
   - low bandwidth support
   - session brokerage support
   - client side mass storage mounting support
   - audio support
   - authentication by smartcard and USB stick

This Python module allows you to integrate X2Go client support into your
Python applications by providing a Python-based X2Go client API.
%endif # with_python3


%prep
%setup -q
# Remove shbang from library scipts
find x2go -name '*.py' | xargs sed -i '1s|^#!/usr/bin/env python||'
# Python3
%if 0%{?with_python3}
rm -rf %{py3dir}
cp -a . %{py3dir}
2to3 --write --nobackups %{py3dir}
%endif # with_python3


%build
%{__python} setup.py build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif # with_python3

# Build the docs
mkdir -p epydoc/html
epydoc --debug -n "Python X2Go" -u http://www.x2go.org -v --html --no-private -o epydoc/html x2go/


%install
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif # with_python3
%{__python} setup.py install --skip-build --root %{buildroot}
%if 0%{?fdupes:1}
%fdupes %buildroot/%_prefix
%endif


%files
%defattr(-,root,root)
%doc COPYING README* TODO
%{python_sitelib}/*

%files doc
%defattr(-,root,root)
%doc epydoc/html


%changelog
