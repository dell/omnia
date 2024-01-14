FROM rockylinux:8.8

WORKDIR /app

# why this is not part of prereq.sh ?
RUN dnf install -y python38 iproute && dnf clean all

# prereq
RUN echo "SELINUX=disabled" > /etc/selinux/config
COPY prereq.sh .
RUN bash -euxo pipefail ./prereq.sh

# why this is not part of prereq.sh ?
# see provision/roles/provision_validation/tasks/package_installation.yml
RUN dnf install -y \
  python3-netaddr \
  openssl \
  dos2unix \
  net-snmp \
  net-snmp-utils \
  sshpass \
  python3-pexpect \
&& dnf clean all

# why above RPMs are not enough ?
RUN python3 -m pip install --no-cache-dir netaddr pexpect

# why this is not part of prereq.sh ?
# see telemetry/roles/omnia_telemetry_cp/tasks/python_package_installation.yml
RUN python3 -m pip install --no-cache-dir pyinstaller psutil

ENTRYPOINT ["ansible-playbook"]
CMD ["prepare_cp.yml", "-vv"]