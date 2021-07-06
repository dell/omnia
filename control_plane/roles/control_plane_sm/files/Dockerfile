FROM centos:8

RUN dnf -y update && dnf clean all

RUN dnf install -y epel-release

RUN dnf groupinstall "Infiniband Support" -y

RUN dnf install -y opensm

COPY opensm.conf /etc/rdma/opensm.conf

COPY start.sh /

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]