# Dockerfile for creating the management network container

FROM centos:8

# RPM REPOs
RUN dnf install -y \
    epel-release \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN dnf install dhcp-server -y
RUN yum install -y \
  ansible \
  cronie \
  net-tools \
  && yum clean all \
  &&  rm -rf /var/cache/yum

RUN mkdir /root/omnia

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf

RUN systemctl enable dhcpd

CMD ["sbin/init"]