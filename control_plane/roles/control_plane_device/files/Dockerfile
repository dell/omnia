# Dockerfile for creating the management network container
FROM rockylinux/rockylinux:8.5

# RPM REPOs
RUN dnf install -y \
    epel-release \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN dnf install -y dhcp-server
RUN dnf install -y python3-netaddr
RUN yum install -y \
  ansible \
  cronie \
  tftp\
  tftp-server\
  xinetd \
  net-tools \
  && yum clean all \
  &&  rm -rf /var/cache/yum

RUN mkdir /root/omnia

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf
COPY tftp /etc/xinetd.d/tftp
COPY inventory_creation.yml /root/
COPY mngmnt_container_configure.yml /root/

RUN systemctl enable tftp
RUN systemctl enable dhcpd

CMD ["sbin/init"]
