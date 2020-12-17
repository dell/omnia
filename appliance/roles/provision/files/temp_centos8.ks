#platform=x86, AMD64, or Intel EM64T
#version=DEVEL
# Firewall configuration
firewall --disabled
# Install OS instead of upgrade
install
# Use network installation
url --url http://ip/cblr/links/CentOS8-x86_64/
#repo --name="CentOS" --baseurl=cdrom:sr0 --cost=100
#Root password
rootpw --iscrypted password
# Use graphical install
#graphical
#Use text mode install
text
#System language
lang en_US
#System keyboard
keyboard us
#System timezone
timezone America/Phoenix --isUtc
# Run the Setup Agent on first boot
#firstboot --enable
# SELinux configuration
selinux --disabled
# Do not configure the X Window System
skipx
# Installation logging level
#logging --level=info
# Reboot after installation
reboot
# System services
services --disabled="chronyd"
ignoredisk --only-use=sda
# Network information
network  --bootproto=dhcp --device=em1 --onboot=on
# System bootloader configuration
bootloader --location=mbr --boot-drive=sda
# Clear the Master Boot Record
zerombr
# Partition clearing information
clearpart --all --initlabel
# Disk partitioning information
part /boot --fstype="xfs" --size=300
part swap --fstype="swap" --size=2048
part pv.01 --size=1 --grow
volgroup root_vg01 pv.01
logvol / --fstype xfs --name=lv_01 --vgname=root_vg01 --size=1 --grow
%packages
@core
%end
