# Dockerfile for creating the management network container
FROM alpine:latest

#Installation of packages
RUN apk add dhcp
RUN apk add ansible
RUN apk add openrc

#Creation of directories and files
RUN mkdir /root/omnia
RUN touch /var/lib/dhcp/dhcpd.leases

#Copy Configuration files
COPY dhcpd.conf  /etc/dhcp/dhcpd.conf
