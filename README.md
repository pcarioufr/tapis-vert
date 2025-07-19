
# Players

## TOP10

### Access Rooms

Access room `abcd-1234` as user `pierre`.
https://tapisvert.pcariou.fr/r/abcd-1234?user=pierre


### Manage Rooms

(Create room `abcd-1234` and) push a new round in room `abcd-1234`, including users `palo`, `lancelot`, `pierre`, `melissa`.
``` bash
curl -XPOST "https://tapisvert.pcariou.fr/api/v1/r/abcd-1234/round?user=palo&user=lancelot&user=pierre&user=melissa"
```

Delete room `abcd-1234`.
``` bash
curl -XDELETE "https://tapisvert.pcariou.fr/v1/abcd-1234f"
```

Rounds expire after 1 hour.


# Ops

"Tapis Verts" is a cloud-native application with a containerized deployment architecture.

## Architecture Overview

The deployment follows a three-layer approach:

- **Infrastructure**: Defined as code using Terraform, targeting OpenStack public cloud (hosted by Infomaniak)
- **Application**: Containerized services orchestrated with Docker Compose
- **Deployment**: Managed through "The Box" - a containerized Linux environment with deployment scripts and dependencies

### Infrastructure Layer (`terraform/`)
The infrastructure is provisioned on OpenStack public cloud using Terraform configuration files. This includes:
- Virtual machines and compute resources
- Network configuration and security groups
- Storage volumes and dependencies

### Application Layer (`services/`)
The application runs as containerized services defined in Docker Compose:
- Web application (Flask-based)
- WebSocket services
- Redis for data persistence
- Nginx as reverse proxy

### Deployment Layer (`box/`)
The Box provides a containerized Linux environment that includes:
- Deployment scripts and automation tools
- Dependencies and utilities for managing the application
- Configuration management for both infrastructure and services

## Getting Started

First, navigate to the box folder and set up the box command alias:
```bash
cd box/
alias box=./box.sh

# Optional: Use -d flag for debug output
box -d terraform plan
box -d deploy -n
```

### 1. Initialize Terraform with Terraform Cloud

The infrastructure state is managed in Terraform Cloud (organization: `pcarioufr`, workspace: `tapis-vert`). You'll need a Terraform Cloud token to initialize and manage the infrastructure.

#### Set up Terraform Cloud Authentication
```bash
# Log in to Terraform Cloud (opens browser for token creation)
box terraform login
```

#### Initialize Terraform
```bash
# Initialize terraform with the remote backend
box terraform init
```

### 2. Operate Infrastructure

#### Configure OpenStack Credentials
Configure OpenStack credentials and settings in [`config/.env`](config/.env).

#### Infrastructure Management Commands
```bash
# Plan infrastructure changes
box terraform plan

# Apply infrastructure changes
box terraform apply

# Destroy infrastructure (when needed)
box terraform destroy
```

#### Output Variables
Get infrastructure information after deployment:
```bash
# Get all outputs in JSON format
box terraform output

# Get specific IP addresses
box terraform output public_ip_v4
box terraform output public_ip_v6
```

Available outputs:
- `public_ip_v4`: IPv4 address of the deployed server
- `public_ip_v6`: IPv6 address of the deployed server

> **Note**: After successful deployment, the infrastructure outputs are automatically updated in [`config/.env`](config/.env) in the auto-generated section. Use `box dns update` to update DNS records manually.

### 3. Operate Application

#### SSH Keypair Management

Before deploying or accessing the remote server, you need to set up SSH keypairs for secure authentication.

```bash
# Generate a new SSH keypair for deployment access
box ssh -n

# Reset known hosts (if connection issues occur)
box ssh -r
```

The SSH keypair is used for:
- Automated deployment scripts
- Manual SSH access to the deployed server
- Secure file transfers and remote commands

> **Note**: Make sure to configure `SSH_HOST` in [`config/.env`](config/.env) with your server's address.

#### SSH Access and Tunneling

```bash
# Open SSH shell to the remote server
box ssh

# Run a specific command remotely
box ssh "docker ps"

# Create SSH tunnel (e.g., for accessing services)
box ssh -L 8000:localhost:8000
box ssh -L 0.0.0.0:8000:localhost:8000
```

#### Configure Application Services
All application settings are configured in [`config/.env`](config/.env) and automatically generated for services during deployment.

#### Application Deployment

Deploy your application services to the remote server using the deployment scripts.

##### Full Deployment
```bash
# Deploy all services and configuration
box deploy

# Dry run - prepare files but don't deploy (useful for testing)
box deploy -n
```

This will:
- Copy source files to a temporary deployment directory (`~/.tmp/deploy/`)
- Process ALL files for template replacement (replace `{{variables}}` with actual config values)
- Generate `services/.env` from configuration in the deployment copy
- Deploy the processed files from temp directory to `/home/ubuntu/services/` on the remote server
- Purge the destination folder before deployment to ensure a clean state
- Source files remain untouched with their template variables

##### Targeted Deployment
```bash
# Deploy only a specific service directory (e.g., webapp)
box deploy -d webapp

# Deploy only the nginx configuration
box deploy -d nginx
```

##### Configuration Patching
```bash
# Update only the environment file without full redeployment
box deploy -p .env

# Update a specific configuration file
box deploy -p nginx/nginx.conf

# Dry run a patch deployment
box deploy -n -p .env
```

> **Note**: Patching (`-p`) updates individual files without purging the destination, useful for quick configuration changes.

##### Restarting Services After Deployment

The deployment commands only push code to the server - the application continues running in its previous state. To apply the changes, you need to restart the services manually:

```bash
# SSH into the server
box ssh

# Navigate to the services directory and restart
cd services/
docker compose down
docker compose up -d

# Or restart specific services
docker compose restart webapp
docker compose restart nginx
```

## DNS Management

Manage your domain's DNS records automatically with the Infomaniak API:

```bash
# View current DNS zone records
box dns get

# Update subdomain records with config values (DOMAIN, SUBDOMAIN, PUBLIC_IP_V4, PUBLIC_IP_V6)
box dns update
```

> **Note**: Configure `INFOMANIAK_TOKEN` in [`config/.env`](config/.env) for automatic DNS sync after infrastructure deployment. The DNS operations work on the `DOMAIN` (DNS zone) and will automatically find and update existing A/AAAA records for the specified subdomain. If records don't exist, they will be created automatically.

# Resources

## Websockets

https://medium.com/@nandagopal05/scaling-websockets-with-pub-sub-using-python-redis-fastapi-b16392ffe291
https://medium.com/@nmjoshi/getting-started-websocket-with-fastapi-b41d244a2799

https://www.uvicorn.org/deployment/#built-in

https://www.geeksforgeeks.org/fast-api-gunicorn-vs-uvicorn/
https://www.pythoniste.fr/python/fastapi/les-differences-entre-les-frameworks-flask-et-fastapi/

https://asgi.readthedocs.io/en/latest/introduction.html
https://realpython.com/python-async-features/


https://fastapi.tiangolo.com/advanced/websockets/#handling-disconnections-and-multiple-clients
