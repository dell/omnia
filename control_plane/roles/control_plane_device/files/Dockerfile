# Dockerfile for creating the management network container
FROM alpine:latest

#Installing packages
RUN apk add dhcp
RUN apk add ansible
RUN apk add openrc

#Creation of directories and files
RUN mkdir /root/omnia
RUN mkdir /etc/periodic/5min
RUN touch /var/lib/dhcp/dhcpd.leases

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf
COPY inventory_creation.yml /root/
COPY mngmnt_container_configure.yml /root/
COPY cron_inv /etc/periodic/5min
