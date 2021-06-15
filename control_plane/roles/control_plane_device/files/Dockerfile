# Dockerfile for creating the management network container

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
  ansible \
  cronie \
  tftp\
  tftp-server\
  dhcp \
  xinetd \
  net-tools \
  && yum clean all \
  &&  rm -rf /var/cache/yum

RUN mkdir /root/omnia

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf
COPY tftp /etc/xinetd.d/tftp
COPY mngmnt_container_configure.yml /root/

RUN systemctl enable tftp
RUN systemctl enable dhcpd

CMD ["sbin/init"]

