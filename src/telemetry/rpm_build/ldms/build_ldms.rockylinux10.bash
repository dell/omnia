#!/bin/bash

pkg_file="ovis-ldms.tar.gz"
ARCH=$(uname -m)
PIP_VERSION="26.2.0"
SETUPTOOLS_VERSION="83.0.0"

# fpm and its pinned dotenv are fetched from an explicit source and verified
# against the SHA-256 published by rubygems.org before installation.
GEM_SOURCE="https://rubygems.org"
GEM_CHECKSUMS="c5944793349ae03c432e1780a2ca929d60b88c7d14d52d630db0508c3a8a17d8  dotenv-2.8.1.gem
1ffbf342a89ca97fb5c02e66946c97e2bd5413810f7f440ddf32f00a16052dbf  fpm-1.15.1.gem"

# epel-release comes from the distribution repository (GPG-verified by dnf);
# no unverified download by URL.
echo "Install epel-release"
dnf install -y epel-release

# Doxygen
#dnf config-manager -y --set-enabled powertools

dnf install -y dnf-plugins-core
dnf config-manager --set-enabled crb

echo "Update"
dnf update -y

echo "Install packages"
dnf install -y \
    autoconf \
    automake \
    bison \
    bzip2 \
    curl \
    doxygen \
    flex \
    gcc \
    gettext \
    git \
    gcc-c++ \
    gzip \
    hostname \
    jansson-devel \
    jansson \
    jq \
    libcurl-devel \
    libibverbs \
    libpfm-devel \
    librdkafka \
    librdmacm \
    less \
    libtool \
    m4 \
    make \
    openssl \
    openssl-devel \
    openssl-libs \
    papi-devel \
    pkg-config \
    python3-pyverbs \
    python3 \
    python3-docutils \
    python3-pip \
    python3-pycurl \
    python3-devel \
    python3-Cython \
    platform-python-devel \
    python3-docutils \
    python3-pip \
    rpm-build \
    rsync \
    rubygems \
    ruby \
    ruby-devel \
    tree \
    vim \
    wget \
    which 
# Install slurm packages
dnf install -y \
    slurm \
    slurm-devel

# Upgrade pip to fix CVE-2026-13346, CVE-2026-8643 and setuptools to fix CVE-2026-59890
echo "Upgrade pip to ${PIP_VERSION} and setuptools to ${SETUPTOOLS_VERSION}"
python3 -m pip install --upgrade --ignore-installed \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}"
python3 - "$PIP_VERSION" "$SETUPTOOLS_VERSION" <<'EOF' || exit 1
import sys
from importlib.metadata import version
for pkg, expected in (("pip", sys.argv[1]), ("setuptools", sys.argv[2])):
    found = version(pkg)
    print(f"{pkg}=={found}")
    # Normalize versions for comparison (e.g., 26.2 == 26.2.0)
    f_parts = found.split('.')
    e_parts = expected.split('.')
    # Pad shorter version with zeros
    while len(f_parts) < len(e_parts):
        f_parts.append('0')
    while len(e_parts) < len(f_parts):
        e_parts.append('0')
    if tuple(map(int, f_parts)) < tuple(map(int, e_parts)):
        sys.exit(f"ERROR: {pkg} {found} < {expected}")
EOF
#--------------------------------
# CLEAN
#--------------------------------
echo "[>>] Clean previous install"
if [ -f "$pkg_file" ]; then
  rm -rf "$pkg_file"
fi
rm -f -- ./*.rpm
find ./ -name "*.deb" -delete
for i in \
  /app \
  /opt/ovis-ldms \
  /app/etc/ldms \
  /app/etc/systemd/system/ldmsd.kokkos.service \
  /app/etc/systemd/system/ldmsd.aggregator.service \
  /app/etc/systemd/system/ldmsd.sampler.service \
  lib/etc/ld.so.conf.d/ovis-ld-so.conf \
  "$pkg_file" \
; do
  if [ -e "$i" ]; then
    echo "[>>]  Delete $i"
    rm -rf "$i"
  fi
done
echo "[>>] Remove old rpm and tar.gz"
rm -rf ovis-ldms.{rpm,tar.gz}
if [ -d "/build/libserde" ]; then
    rm -rf "/build/libserde"
fi
echo "[>>] Clean source tree"
rm -rf .version
make uninstall
make distclean
make clean
make maintainer-clean
echo "[>>] Clean isn't clean. Remove any file with an .in file"
find . -name '*.in' -print0 | while IFS= read -r -d '' f; do
  base="${f%.in}"
  printf 'Remove %s\n' "$base"
  rm -rf -- "$base"
done
rm -rf autom4te.cache config.cache

#--------------------------------
# BUILD 
#--------------------------------
echo "[>>] Get in source dir"
#popd
#rpm -i datacenter-gpu-manager-2.2.3-1-x86_64.rpm 
set -xe
# Only patch a real DCGM header, and only once. OVIS builds the DCGM sampler
# only when libdcgm is present, so the header is otherwise not used.
dcgm_header="/usr/include/dcgm_api_export.h"
if [ -f "$dcgm_header" ] && ! grep -q 'DCGM_PUBLIC_API' "$dcgm_header"; then
  echo "#define DCGM_PUBLIC_API" >> "$dcgm_header"
fi
echo "[--] Build ldms"
echo "[>>] autogen (runs autoreconf internally)"
./autogen.sh
echo "[>>] configure"
/builds/scripts/configure.sh
echo "[>>] make"
make -j 10
echo "[>>] make install"
make install
echo "[>>] Find python3 site packages"

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_SITE_PKGS="$(python3 -m site --user-site)"
echo "PYTHON_VERSION=$PYTHON_VERSION"
echo "PYTHON_SITE_PKGS=$PYTHON_SITE_PKGS"

#--------------------------------
# ASSEBLE PACKAGE TREE
#--------------------------------
echo "[>>] Make package tree staging area: /app"
mkdir -p \
  /app/etc/profile.d \
  /app/etc/sysconfig \
  /app/lib/systemd/system \
  /app/opt \
  /app/${PYTHON_SITE_PKGS} \
  /app/usr/share
echo "[>>] Stage /usr/share/man"
mv /opt/ovis-ldms/share/man /app/usr/share/
echo "[>>] Stage /opt/ovis-ldms"
mv /opt/ovis-ldms /app/opt/
rsync -a /app/opt/ovis-ldms/share/doc/ovis-ldms/sample_init_scripts/opt/etc/systemd /app/opt/ovis-ldms/etc/
rsync -a /app/opt/ovis-ldms/share/doc/ovis-ldms/sample_init_scripts/opt/etc/ldms /app/opt/ovis-ldms/etc/
echo "[>>] Stage /etc"
ln -s /opt/ovis-ldms/etc/profile.d/set-ovis-variables.sh /app/etc/profile.d/set-ovis-variables.sh
echo "[>>] Stage /lib/systemd/system"
ln -s /opt/ovis-ldms/etc/systemd/system/nersc-ldmsd.sampler.service /app/lib/systemd/system/nersc-ldmsd.sampler.service
echo "[>>] Stage ${PYTHON_SITE_PKGS}"
ln -s /opt/ovis-ldms/lib/${PYTHON_VERSION}/ldmsd /app/${PYTHON_SITE_PKGS}/
ln -s /opt/ovis-ldms/lib/${PYTHON_VERSION}/ovis_ldms /app/${PYTHON_SITE_PKGS}/

#--------------------------------
# PACKAGE
#--------------------------------
echo "[>>] Bundle"
ls -tlr /app
tar -C /app -czvpf "$pkg_file" .

echo "[>>] Build Product"
du -sh "$pkg_file"

echo "[>>] install fpm"

# Workaround due pleaserun hard dependency on ruby-3.0
# REF: https://github.com/jordansissel/fpm/issues/2048
# dotenv is installed first so fpm's dependency on it is already satisfied.
gem_dir="$(mktemp -d)"
(
  cd "$gem_dir"
  gem fetch dotenv -v 2.8.1 --clear-sources --source "$GEM_SOURCE"
  gem fetch fpm -v 1.15.1 --clear-sources --source "$GEM_SOURCE"
  printf '%s\n' "$GEM_CHECKSUMS" | sha256sum -c -
  gem install --no-document --conservative --clear-sources --source "$GEM_SOURCE" ./dotenv-2.8.1.gem
  gem install --no-document --conservative --clear-sources --source "$GEM_SOURCE" ./fpm-1.15.1.gem
)
rm -rf -- "$gem_dir"

fpm --version
echo "[>>] Build RPM with fpm"
fpm \
--input-type tar \
--output-type rpm \
--name ovis-ldms \
--version $(cat .version) \
--iteration 1 \
--depends bash \
--depends python3-Cython \
--depends python3-devel \
--directories=/opt/ovis-ldms \
--post-uninstall /builds/scripts/rpm_postuninstall.txt \
--license "GPLv2 or BSD" \
--rpm-group root \
--description "This package provides the LDMS commands and libraries.\n* ldmsd: the LDMS daemon, which can run as sampler or aggregator (or both).\n* ldms_ls: the tool to list metric information of an ldmsd.\n* ldmsctl: the tool to control an ldmsd." \
--rpm-summary "LDMS - Lighweight Distributed Metric Service" \
--package ovis-ldms-$(cat .version).${ARCH}.rpm \
"$pkg_file"

echo "[>>] List rpm created"
ls -tlr *tar.gz *.rpm
echo "[>>] List files in rpm"
rpm -qlp "ovis-ldms-$(cat .version).${ARCH}.rpm"
echo "[>>] Show rpm scripts"
rpm -qp --scripts "ovis-ldms-$(cat .version).${ARCH}.rpm"
echo "[>>] Show rpm info"
rpm -qi "ovis-ldms-$(cat .version).${ARCH}.rpm"
echo "[--] Success"
