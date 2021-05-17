#!/bin/bash

HOSTNAME=
IPADDR=
MAC=
INTERFACE="em1"
PROFILE="CentOS7-x86_64"

cobbler system remove --name=$HOSTNAME 2>&1 > /dev/null

cobbler system add --name=$HOSTNAME --hostname=$HOSTNAME --profile=$PROFILE

cobbler system edit --name=$HOSTNAME --interface=$INTERFACE --mac=$MAC

cobbler system edit --name=$HOSTNAME --kopts="ksdevice=$MAC nomodeset consoleblank=0"

cobbler system edit --name=$HOSTNAME --kopts-post="nomodeset consoleblank=0"

#cobbler sync

