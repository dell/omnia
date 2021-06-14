#version=DEVEL

# Use network installation
url --url http://ip/cblr/links/CentOS7-x86_64/

# Install OS instead of upgrade
install

# Use text install
text

# SELinux configuration
selinux --disabled

# Firewall configuration
firewall --disabled

# Do not configure the X Window System
skipx

# Run the Setup Agent on first boot
#firstboot --enable
ignoredisk --only-use=sda

# Keyboard layouts
keyboard us

# System language
lang en_US

# Network information
network  --bootproto=dhcp --device=nic --onboot=on

# Root password
rootpw --iscrypted password

# System services
services --enabled="chronyd"

# System timezone
timezone --utc ks_timezone

# System bootloader configuration
bootloader --location=mbr --boot-drive=sda

# Partition clearing information
clearpart --all --initlabel --drives=sda

# Clear the Master Boot Record
zerombr

# Disk Partitioning
partition /boot/efi --asprimary --fstype=vfat --label EFI  --size=200
partition /boot     --asprimary --fstype=ext4 --label BOOT --size=500
partition /         --asprimary --fstype=ext4 --label ROOT --size=4096 --grow

# Reboot after installation
reboot

%packages
@core
net-tools
%end