#!/bin/sh
# Removed obsolete -P 4 option (thread pool configuration is now automatic in newer LDMS versions)
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/libserdes.so /opt/ovis-ldms/sbin/ldmsd -F -c ${LDMSD_CONF} -m 128M -a ${LDMSD_AUTH_PLUGIN} -A ${LDMSD_AUTH_OPTION} -x sock:${LDMSD_PORT} -v INFO
