
terraform {

    cloud {
        organization = "pcarioufr"
        workspaces {
            name = "tapis-vert"
        }
    }

    required_providers {
        openstack = {
            source  = "terraform-provider-openstack/openstack"
            version = "2.0.0"
        }
    }

}

provider "openstack" {
    auth_url          = "https://api.pub1.infomaniak.cloud/identity/v3"
    region            = "dc3-a"
    user_name         = "${var.openstack_username}"
    password          = "${var.openstack_password}"
    user_domain_name  = "default"
    project_domain_id = "default"
    tenant_id         = "${var.tenant_id}"
    tenant_name       = "${var.tenant_name}"
}
