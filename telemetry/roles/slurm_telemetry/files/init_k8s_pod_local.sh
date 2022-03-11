#!/bin/bash

echo 'manager_node_ip manager_node_hostname' >> /etc/hosts
ssh-keyscan -H manager_node_hostname >> /root/.ssh/known_hosts
ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -q -N "" -y
sshpass -p 'os_passwd' ssh-copy-id 'root@manager_node_ip'