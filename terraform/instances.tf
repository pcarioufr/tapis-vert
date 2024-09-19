
resource "openstack_compute_keypair_v2" "keys" {
    name       = "keys"
    public_key = join("\n", var.sshkeys)
}


resource "openstack_networking_port_v2" "port_v4v6" {

    network_id = data.openstack_networking_network_v2.extv4v6.id

    security_group_ids = [
        openstack_networking_secgroup_v2.ssh.id, 
        openstack_networking_secgroup_v2.web.id, 
        openstack_networking_secgroup_v2.icmp.id,
    ]

}


resource "openstack_compute_instance_v2" "tapis-vert" {

    name            = "tapis-vert-1"
    flavor_name     = "a1-ram2-disk0"
    key_pair        = "keys"

    network {
        port = openstack_networking_port_v2.port_v4v6.id
    }

    block_device {
        uuid                  = "a4ec27be-ab61-42f6-9aae-c6b6f975a567" # Ubuntu Jammy
        source_type           = "image"
        destination_type      = "volume"
        boot_index            = 0
        delete_on_termination = true
        volume_size           = 10
    }

    block_device {
        uuid                  = openstack_blockstorage_volume_v3.data.id
        source_type           = "volume"
        destination_type      = "volume"
        boot_index            = 1
    }

    user_data = data.cloudinit_config.tapis-vert.rendered

}

resource "openstack_blockstorage_volume_v3" "data" {
    name    = "data"
    size    = 20
}


data "cloudinit_config" "tapis-vert" {

    part {
        filename     = "cloud-init.yaml"
        content_type = "text/cloud-config"
        content = templatefile("${path.module}/cloud-init.yaml", { 
            MOUNT_DISK      = "sdb"
            PARTITION_NAME  = "sdb1"
            MOUNT_NAME      = "data"
            MOUNT_PATH      = "/mnt/data"
        })
    }

}
