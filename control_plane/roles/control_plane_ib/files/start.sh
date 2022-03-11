#!/bin/bash

/usr/libexec/rdma-init-kernel

exec /usr/sbin/opensm -F /etc/rdma/opensm.conf
