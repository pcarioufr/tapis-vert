#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done



# Update config with terraform outputs
update_config_with_outputs() {
    notice "Updating config with terraform outputs..."
    
    # Get terraform outputs
    PUBLIC_IP_V4=$(terraform ${TF_OPTS} output -raw public_ip_v4 2>/dev/null)
    PUBLIC_IP_V6=$(terraform ${TF_OPTS} output -raw public_ip_v6 2>/dev/null)
    
    if [ -n "$PUBLIC_IP_V4" ]; then
        # Update the auto-generated section in config/.env
        sed -i.bak "/# TERRAFORM OUTPUTS/,/^$/c\\
# =============================================================================\\
# TERRAFORM OUTPUTS (AUTO-GENERATED - DO NOT EDIT MANUALLY)\\
# =============================================================================\\
SSH_HOST=\"ubuntu@${PUBLIC_IP_V4}\"\\
PUBLIC_IP_V4=\"${PUBLIC_IP_V4}\"\\
PUBLIC_IP_V6=\"${PUBLIC_IP_V6}\"\\
" /data/config/.env
        
        notice "Updated SSH_HOST to ubuntu@${PUBLIC_IP_V4}"
        notice "Updated PUBLIC_IP_V4 to ${PUBLIC_IP_V4}"
        if [ -n "$PUBLIC_IP_V6" ]; then
            notice "Updated PUBLIC_IP_V6 to ${PUBLIC_IP_V6}"
        fi
    else
        debug "No terraform outputs found, skipping config update"
    fi
}

# Export Terraform variables (config already loaded by main)
export TF_VAR_openstack_username="$OS_USERNAME"
export TF_VAR_openstack_password="$OS_PASSWORD"
export TF_VAR_tenant_id="$OS_TENANT_ID"
export TF_VAR_tenant_name="$OS_TENANT_NAME"

# Export SSH keys array (convert from string to array format for Terraform)
if [ -n "$SSH_PUBLIC_KEY" ]; then
    export TF_VAR_sshkeys="[\"$SSH_PUBLIC_KEY\"]"
fi

debug "Exported Terraform variables"

debug "terraform $@"

CMD=${1}
TF_OPTS="-chdir=/data/terraform"

if [ "$CMD" == "login" ] ; then
    terraform login
    exit 0 
fi

if [ "$CMD" == "init" ] ; then
    terraform ${TF_OPTS} init ${@:2}
    exit 0 
fi

if [ "$CMD" == "output" ] ; then
    echo $(terraform ${TF_OPTS} output -json ${@:2}) | jq -r 
    exit 0 
fi

# Run terraform command
terraform ${TF_OPTS} ${@}
TERRAFORM_EXIT_CODE=$?

# If terraform apply was successful, update config with outputs
if [ "$CMD" == "apply" ] && [ $TERRAFORM_EXIT_CODE -eq 0 ]; then
    update_config_with_outputs
    
    # TODO: Auto-sync DNS when ready
    # if [ -n "$INFOMANIAK_TOKEN" ]; then
    #     notice "Auto-syncing DNS records with new IP addresses..."
    #     /opt/box/dns.sh update
    # else
    #     notice "INFOMANIAK_TOKEN not configured, skipping DNS sync"
    # fi
    
    notice "Infrastructure updated. Run 'box dns update' to update DNS records manually."
fi

exit $TERRAFORM_EXIT_CODE
