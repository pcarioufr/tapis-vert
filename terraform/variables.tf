
variable "sshkeys" {
    type    = list
}

variable "openstack_username" {
  type    = string
}

variable "tenant_id" {
  type    = string
}

variable "tenant_name" {
  type    = string
}

variable "openstack_password" {
  type    = string
  sensitive   = true
}


output "public_ip_v6" {
    value = openstack_compute_instance_v2.tapis-vert.access_ip_v6
}

output "public_ip_v4" {
    value = openstack_compute_instance_v2.tapis-vert.access_ip_v4
}
