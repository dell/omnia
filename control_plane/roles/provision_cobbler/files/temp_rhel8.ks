#version=RHEL8

# Use network installation
url --url http://ip:port/cblr/links/redhat-x86_64/

# SELinux configuration
selinux --disabled

# Firewall configuration
firewall --disabled

# text install
text

# Do not configure the X Window System
skipx

# Keyboard layouts
keyboard us

# System language
lang ks_language

# Network information
network  --bootproto=dhcp --device=link --onboot=on --activate

# Root password
rootpw --iscrypted ks_password

# System services
services --enabled="chronyd"

# System timezone
timezone --utc ks_timezone

# System bootloader configuration
bootloader --location=mbr

# Tell it to blow away the master boot record on the hard drive
zerombr

# Tell it to do a dumb move and blow away all partitions
clearpart --all --initlabel

# Auto partitiong
autopart

# Reboot after installation
reboot

%packages
@^minimal-environment
net-tools
python3
%end

%include /tmp/bootdisk.cfg

%pre --log=/root/ks-pre.log

# Fetching NIC information
for nic in `cut -f 1 -d : /proc/net/dev | awk 'NR>2'`; do
  echo "network  --bootproto=dhcp --device=${nic} --onboot=on --activate" >> /tmp/bootdisk.cfg
done

# Fetching BOSS card information
find /dev -name "*DELLBOSS*" -printf %P"\n" | egrep -v -e part -e scsi | head -1 > /tmp/bossdisk.txt

if [ -s /tmp/bossdisk.txt ]
then
        echo "#BOSS controller present" >> /tmp/bootdisk.cfg
        echo "ignoredisk --only-use=`find /dev -name '*DELLBOSS*' -printf %P'\n' | egrep -v -e part -e scsi | head -1`" >> /tmp/bootdisk.cfg
else
        echo "#BOSS controller not present" >> /tmp/bootdisk.cfg
fi

%end
