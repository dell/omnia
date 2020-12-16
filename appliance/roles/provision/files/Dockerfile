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
  debmirror \
  curl \
  wget \
  rsync \
  httpd\
  dhcp\
  dnsmasq\
  xinetd \
  net-tools \
  memtest86+ \
  && yum clean all \
  &&  rm -rf /var/cache/yum

#Copy Configuration files
COPY settings /etc/cobbler/settings
COPY dhcp.template  /etc/cobbler/dhcp.template
COPY dnsmasq.template /etc/cobbler/dnsmasq.template
COPY modules.conf  /etc/cobbler/modules.conf
COPY tftp /etc/xinetd.d/tftp
COPY .users.digest /etc/cobbler/users.digest
COPY kickstart.yml /root
COPY centos8.ks /var/lib/cobbler/kickstarts
COPY first-sync.sh /usr/local/bin/first-sync.sh

EXPOSE 69 80 443 25151

VOLUME [ "/var/www/cobbler", "/var/lib/cobbler/backup", "/mnt" ]

RUN systemctl enable cobblerd
RUN systemctl enable httpd
RUN systemctl enable rsyncd
RUN systemctl enable dnsmasq

#RUN ansible-playbook /root/kickstart.yml

CMD ["sbin/init"]
