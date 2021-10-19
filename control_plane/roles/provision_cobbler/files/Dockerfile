FROM centos:8.3.2011

# RPM REPOs
RUN dnf install -y \
    epel-release \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN dnf update -y \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN dnf install -y git
RUN git clone -b v3.2.2 https://github.com/cobbler/cobbler.git
RUN cd cobbler/

RUN mkdir /root/omnia

RUN dnf install -y mod_ssl \
        python3-librepo \
        python3-schema \
        syslinux \
        wget \
        dhcp-server \
        pykickstart \
        dnf-plugins-core \
        cronie \
        xinetd \
        python3-coverage \
        python3-cheetah \
        python3-netaddr \
        python3-distro \
        python3-devel \
        python3-future \
        python3-mod_wsgi \
        gcc \
        xinetd \
        epel-rpm-macros \
        rpm-build \
        ansible \
        make \
        grub2-efi-x64-modules \
        efibootmgr \
        && dnf clean all \
        &&  rm -rf /var/cache/dnf

RUN yum install -y  grub2-efi-x64 shim-x64 
RUN yum install -y yum-utils
RUN dnf config-manager --set-enabled powertools
RUN dnf install -y python3-sphinx
RUN pip3 install wheel

#Copy Configuration files
COPY cobbler_settings /etc/cobbler/settings.yaml
COPY temp_dhcp.template  /etc/cobbler/dhcp.template
COPY modules.conf  /etc/cobbler/modules.conf
COPY tftp /etc/xinetd.d/tftp
COPY .users.digest /etc/cobbler/users.digest
COPY cobbler_configurations.yml /root
COPY tftp.yml /root
COPY inventory_creation.yml /root

EXPOSE 69 80 443 25151

VOLUME [ "/var/www/cobbler", "/var/lib/cobbler/backup", "/mnt" ]

RUN systemctl enable httpd
RUN systemctl enable dhcpd

CMD ["sbin/init"]
