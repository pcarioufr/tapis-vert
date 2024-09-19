#### EXTERNAL NETWORK ######################

data "openstack_networking_network_v2" "extv4v6" {
  name = "ext-net1"
}



#### SECURITY GROUPS ######################

## SSH ######################

resource "openstack_networking_secgroup_v2" "ssh" {
    name        = "ssh"
    description = "ssh 22"
}

resource "openstack_networking_secgroup_rule_v2" "ssh_22_v6" {
    direction         = "ingress"
    ethertype         = "IPv6"
    protocol          = "tcp"
    port_range_min    = 22
    port_range_max    = 22
    remote_ip_prefix  = "::/0"
    security_group_id = "${openstack_networking_secgroup_v2.ssh.id}"
}

resource "openstack_networking_secgroup_rule_v2" "ssh_22_v4" {
    direction         = "ingress"
    ethertype         = "IPv4"
    protocol          = "tcp"
    port_range_min    = 22
    port_range_max    = 22
    remote_ip_prefix  = "0.0.0.0/0"
    security_group_id = "${openstack_networking_secgroup_v2.ssh.id}"
}


## WEB ######################

resource "openstack_networking_secgroup_v2" "web" {
    name        = "web"
    description = "web 80 443"
}

resource "openstack_networking_secgroup_rule_v2" "web_80_v6" {
    direction         = "ingress"
    ethertype         = "IPv6"
    protocol          = "tcp"
    port_range_min    = 80
    port_range_max    = 80
    remote_ip_prefix  = "::/0"
    security_group_id = "${openstack_networking_secgroup_v2.web.id}"
}

resource "openstack_networking_secgroup_rule_v2" "web_80_v4" {
    direction         = "ingress"
    ethertype         = "IPv4"
    protocol          = "tcp"
    port_range_min    = 80
    port_range_max    = 80
    remote_ip_prefix  = "0.0.0.0/0"
    security_group_id = "${openstack_networking_secgroup_v2.web.id}"
}

resource "openstack_networking_secgroup_rule_v2" "web_443_v6" {
    direction         = "ingress"
    ethertype         = "IPv6"
    protocol          = "tcp"
    port_range_min    = 443
    port_range_max    = 443
    remote_ip_prefix  = "::/0"
    security_group_id = "${openstack_networking_secgroup_v2.web.id}"
}

resource "openstack_networking_secgroup_rule_v2" "web_443_v4" {
    direction         = "ingress"
    ethertype         = "IPv4"
    protocol          = "tcp"
    port_range_min    = 443
    port_range_max    = 443
    remote_ip_prefix  = "0.0.0.0/0"
    security_group_id = "${openstack_networking_secgroup_v2.web.id}"
}


## ICMP ######################

resource "openstack_networking_secgroup_v2" "icmp" {
    name        = "icmp"
    description = "icmp"
}

resource "openstack_networking_secgroup_rule_v2" "icmp_v6" {
    direction         = "ingress"
    ethertype         = "IPv6"
    protocol          = "ipv6-icmp"
    remote_ip_prefix  = "::/0"
    security_group_id = "${openstack_networking_secgroup_v2.icmp.id}"
}

resource "openstack_networking_secgroup_rule_v2" "icmp_v4" {
    direction         = "ingress"
    ethertype         = "IPv4"
    protocol          = "icmp"
    remote_ip_prefix  = "0.0.0.0/0"
    security_group_id = "${openstack_networking_secgroup_v2.icmp.id}"
}
