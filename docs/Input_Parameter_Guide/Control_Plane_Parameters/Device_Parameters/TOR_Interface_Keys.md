# Accepted Interface Keys on Top Of the Rack Switches

Interface key name	|	Type	|	Description
---------	|   ----	|	-----------
desc	|	string	|	Configures a single line interface description
portmode	|	string	|	Configures port mode according to the device type
switchport	|	boolean: true, false*	|	Configures an interface in L2 mode
admin	|	string: up, down*	|	Configures the administrative state for the interface; configuring the value as administratively "up" enables the interface; configuring the value as administratively "down" disables the interface
mtu	|	integer	|	Configures the MTU size for L2 and L3 interfaces (1280 to 65535)
speed	|	string: auto, 1000, 10000, 25000, ...	|	Configures the speed of the interface
fanout	|	string: dual, single; string:10g-4x, 40g-1x, 25g-4x, 100g-1x, 50g-2x (os10)	|	Configures fanout to the appropriate value
suppress_ra	|	string: present, absent	|	Configures IPv6 router advertisements if set to present
ip_type_dynamic	|	boolean: true, false	|	Configures IP address DHCP if set to true (ip_and_mask is ignored if set to true)
ipv6_type_dynamic	|	boolean: true, false	|	Configures an IPv6 address for DHCP if set to true (ipv6_and_mask is ignored if set to true)
ipv6_autoconfig	|	boolean: true, false	|	Configures stateless configuration of IPv6 addresses if set to true (ipv6_and_mask is ignored if set to true)
vrf	|	string	|	Configures the specified VRF to be associated to the interface
min_ra	|	string	|	Configures RA minimum interval time period
max_ra	|	string	|	Configures RA maximum interval time period
ip_and_mask	|	string	|	Configures the specified IP address to the interface
ipv6_and_mask	|	string	|	Configures a specified IPv6 address to the interface
virtual_gateway_ip	|	string	|	Configures an anycast gateway IP address for a VXLAN virtual network as well as VLAN interfaces
virtual_gateway_ipv6	|	string	|	Configures an anycast gateway IPv6 address for VLAN interfaces
state_ipv6	|	string: absent, present*	|	Deletes the IPV6 address if set to absent
ip_helper	|	list	|	Configures DHCP server address objects (see ip_helper.*)
ip_helper.ip	|	string (required)	|	Configures the IPv4 address of the DHCP server (A.B.C.D format)
ip_helper.state	|	string: absent, present*	|	Deletes the IP helper address if set to absent
flowcontrol	|	dictionary	|	Configures the flowcontrol attribute (see flowcontrol.*)
flowcontrol.mode	|	string: receive, transmit	|	Configures the flowcontrol mode
flowcontrol.enable	|	string: on, off	|	Configures the flowcontrol mode on
flowcontrol.state	|	string: absent, present	|	Deletes the flowcontrol if set to absent
ipv6_bgp_unnum	|	dictionary	|	Configures the IPv6 BGP unnum attributes (see ipv6_bgp_unnum.*) below
ipv6_bgp_unnum.state	|	string: absent, present*	|	Disables auto discovery of BGP unnumbered peer if set to absent
ipv6_bgp_unnum.peergroup_type	|	string: ebgp, ibgp	|	Specifies the type of template to inherit from
stp_rpvst_default_behaviour	|	boolean: false, true	|	Configures RPVST default behavior of BPDU's when set to True, which is default
