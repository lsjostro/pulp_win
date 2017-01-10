%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%define pulp_admin 1
%define pulp_server 1

# define required pulp platform version.
%define pulp_version 2.10.1

%define inst_prefix pulp_win

# ---- Pulp (win) --------------------------------------------------------------

Name: pulp-win
Version: 3.0
Release: 1%{?dist}
Summary: Support for Windows content in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: https://github.com/lsjostro/
Source0: https://github.com/lsjostro/pulp_win/releases/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
Provides a collection of platform plugins, client extensions and agent
handlers that provide Windows support.

%prep
%setup -q

%build

pushd common
%{__python} setup.py build
popd

%if %{pulp_admin}
pushd extensions_admin
%{__python} setup.py build
popd
%endif # End pulp_admin if block

%if %{pulp_server}
pushd plugins
%{__python} setup.py build
popd
%endif # End pulp_server if block

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/%{_sysconfdir}/pulp

pushd common
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

%if %{pulp_admin}
pushd extensions_admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
%endif # End pulp_admin if block

%if %{pulp_server}
pushd plugins
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins
%endif # End pulp_server if block

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}


# ---- Common --------------------------------------------------------------

%package -n python-%{name}-common
Summary: Pulp Windows support common library
Group: Development/Languages
Obsoletes: pulp-win-plugins-admin <= 2.4.0

%description -n python-%{name}-common
A collection of modules shared among all Win components.

%files -n python-%{name}-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/%{inst_prefix}
%{python_sitelib}/%{inst_prefix}_common*.egg-info
%{python_sitelib}/%{inst_prefix}/__init__.py*
%{python_sitelib}/%{inst_prefix}/extensions/__init__.py*
%{python_sitelib}/%{inst_prefix}/common/
%doc LICENSE

# ---- Plugins -----------------------------------------------------------------
%if %{pulp_server}
%package plugins
Summary: Pulp Win plugins
Group: Development/Languages
Requires: python-%{name}-common = %{version}-%{release}
Requires: pulp-server
Requires: pulp-rpm-plugins
Requires: msitools
Obsoletes: pulp-win-plugins-server <= 2.4.0

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Win specific support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}/plugins/
%{python_sitelib}/%{inst_prefix}_plugins*.egg-info
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{inst_prefix}.conf
%{_usr}/lib/pulp/plugins/types/win.json
%defattr(-,apache,apache,-)
%defattr(-,root,root,-)
%doc LICENSE
%endif # End pulp_server if block


# ---- Admin Extensions --------------------------------------------------------
%if %{pulp_admin}
%package admin-extensions
Summary: The Win admin client extensions
Group: Development/Languages
Requires: pulp-admin-client
Requires: python-%{name}-common = %{version}-%{release}

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Win specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}_extensions_admin*.egg-info
%{python_sitelib}/%{inst_prefix}/extensions/__init__.py*
%{python_sitelib}/%{inst_prefix}/extensions/admin/
%doc LICENSE
%endif # End pulp_admin if block

%changelog
* Tue Aug 21 2014 lars sjostrom <lars@radicore.se> - 2.4.0-1
-  initial spec (lars@radicore.se)
