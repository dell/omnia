FROM docker.io/rockylinux/rockylinux:docker_os

RUN dnf install -y epel-release
RUN dnf install dhcp-server -y \
  ansible \
  cronie \
  net-tools
RUN dnf groupinstall "Infiniband Support" -y
RUN dnf install -y opensm
RUN dnf clean all  && \
    rm -rf /var/cache/yum

#Creation of directories and files
RUN mkdir /root/omnia
RUN touch /var/lib/dhcpd/dhcpd.leases

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf
COPY opensm.conf /etc/rdma/opensm.conf
COPY start.sh /

RUN systemctl enable dhcpd
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
CMD ["sbin/init"]
