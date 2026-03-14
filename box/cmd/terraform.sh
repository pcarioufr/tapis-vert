#!/bin/bash

usage() {
    echo "----------------- box terraform -----------------"
    echo "Terraform wrapper with automatic variable export and config sync."
    echo ""
    echo "Usage: box terraform [-h] <command> [args]"
    echo ""
    echo "Options:"
    echo "    -h              show this help"
    echo ""
    echo "Commands:"
    echo "    login           authenticate with Terraform Cloud"
    echo "    init            initialize terraform (accepts extra args)"
    echo "    plan            preview infrastructure changes"
    echo "    apply           apply changes (auto-updates config/.env with new IPs)"
    echo "    output [name]   show outputs as JSON (via jq)"
    echo "    <any>           passed through to terraform as-is"
    echo ""
    echo "After a successful 'apply', PUBLIC_IP_V4 and PUBLIC_IP_V6 are"
    echo "automatically written back to config/.env."
    echo ""
    echo "Examples:"
    echo "    box terraform login                    # Authenticate"
    echo "    box terraform init                     # Initialize"
    echo "    box terraform plan                     # Preview changes"
    echo "    box terraform apply                    # Apply and sync config"
    echo "    box terraform output public_ip_v4      # Get specific output"
    echo ""
    echo "Required config: OS_USERNAME, OS_PASSWORD, OS_TENANT_ID,"
    echo "                 OS_TENANT_NAME, SSH_PUBLIC_KEY"
}

# Update config with terraform outputs
update_config_with_outputs() {
    notice "Updating config with terraform outputs..."
    
    # Get terraform outputs
    PUBLIC_IP_V4=$(terraform ${TF_OPTS} output -raw public_ip_v4 2>/dev/null)
    PUBLIC_IP_V6=$(terraform ${TF_OPTS} output -raw public_ip_v6 2>/dev/null)
    
    if [ -n "$PUBLIC_IP_V4" ]; then
        # Update variables in config/.env file
        update_env_var() {
            local var_name="$1"
            local var_value="$2"
            local config_file="${BOX_REPO_ROOT}/config/.env"
            
            debug "Updating env var ${var_name}=${var_value} in ${config_file}"
            
            if grep -q "^${var_name}=" "$config_file"; then
                # Variable exists, update it
                debug "Found existing ${var_name}, updating value"
                sed "s/^${var_name}=.*/${var_name}=\"${var_value}\"/" "$config_file" > "/tmp/env_update.$$"
                cat "/tmp/env_update.$$" > "$config_file"
                rm -f "/tmp/env_update.$$"
                info "Updated ${var_name} to ${var_value}"
            else
                # Variable doesn't exist, add it
                debug "No existing ${var_name}, adding new entry"
                echo "${var_name}=\"${var_value}\"" >> "$config_file"
                info "Added new variable ${var_name}=${var_value}"
            fi
        }
        
        # Update the terraform output variables
        update_env_var "PUBLIC_IP_V4" "${PUBLIC_IP_V4}"
        update_env_var "PUBLIC_IP_V6" "${PUBLIC_IP_V6}"

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
TF_OPTS="-chdir=${BOX_REPO_ROOT}/terraform"

if [ "$CMD" == "-h" ] || [ "$CMD" == "--help" ] ; then
    usage
    exit 0
fi

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
    #     "$(dirname "$0")/dns.sh" update
    # else
    #     notice "INFOMANIAK_TOKEN not configured, skipping DNS sync"
    # fi
    
    success "Infrastructure updated. Run 'box dns update' to update DNS records manually."
fi

exit $TERRAFORM_EXIT_CODE
