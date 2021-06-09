FROM centos:7

# RPM REPOs
RUN yum install -y \
    epel-release \
    && yum clean all \
    && rm -rf /var/cache/yum

RUN yum update -y \
    && yum clean all \
    && rm -rf /var/cache/yum

RUN yum install -y \
  cobbler \
  cobbler-web \
  ansible \
  pykickstart \
  cronie \
  debmirror \
  curl \
  rsync \
  httpd\
  dhcp \
  xinetd \
  net-tools \
  memtest86+ \
  && yum clean all \
  &&  rm -rf /var/cache/yum

RUN mkdir /root/omnia

#Copy Configuration files
COPY settings /etc/cobbler/settings
COPY dhcp.template  /etc/cobbler/dhcp.template
COPY modules.conf  /etc/cobbler/modules.conf
COPY tftp /etc/xinetd.d/tftp
COPY .users.digest /etc/cobbler/users.digest
COPY kickstart.yml /root
COPY tftp.yml /root
COPY inventory_creation.yml /root
COPY centos7.ks /var/lib/cobbler/kickstarts

EXPOSE 69 80 443 25151

VOLUME [ "/var/www/cobbler", "/var/lib/cobbler/backup", "/mnt" ]

RUN systemctl enable cobblerd
RUN systemctl enable httpd
RUN systemctl enable rsyncd

CMD ["sbin/init"]