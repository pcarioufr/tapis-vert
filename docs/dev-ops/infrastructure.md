# Infrastructure & Deployment Guide

This guide covers the complete infrastructure setup, deployment processes, and operational procedures for Tapis Vert.

## Architecture Overview

Tapis Vert is a cloud-native application with a containerized deployment architecture following a three-layer approach:

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

## 1. Initialize Terraform with Terraform Cloud

The infrastructure state is managed in Terraform Cloud (organization: `pcarioufr`, workspace: `tapis-vert`). You'll need a Terraform Cloud token to initialize and manage the infrastructure.

### Set up Terraform Cloud Authentication
```bash
# Log in to Terraform Cloud (opens browser for token creation)
box terraform login
```

### Initialize Terraform
```bash
# Initialize terraform with the remote backend
box terraform init
```

## 2. Infrastructure Operations

### Configure OpenStack Credentials
Configure OpenStack credentials and settings in [`config/.env`](../../config/.env).

### Infrastructure Management Commands
```bash
# Plan infrastructure changes
box terraform plan

# Apply infrastructure changes
box terraform apply

# Destroy infrastructure (when needed)
box terraform destroy
```

### Output Variables
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

> **Note**: After successful deployment, the infrastructure outputs are automatically updated in [`config/.env`](../../config/.env). Use `box dns update` to update DNS records manually.

## 3. Application Operations

### SSH Keypair Management

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

> **Note**: Make sure to configure `SSH_HOST` in [`config/.env`](../../config/.env) with your server's address.

### SSH Access and Tunneling

```bash
# Open SSH shell to the remote server
box ssh

# Run a specific command remotely
box ssh "docker ps"

# Create SSH tunnel (e.g., for accessing services)
box ssh -L 8000:localhost:8000
box ssh -L 0.0.0.0:8000:localhost:8000
```

### Configure Application Services
All application settings are configured in [`config/.env`](../../config/.env) and automatically generated for services during deployment.

### Application Deployment

Deploy your application services to the remote server using the deployment scripts.

#### Application Deployment
```bash
# Deploy all services and configuration with template processing
box deploy

# Dry run - process templates but don't deploy (useful for testing)
box deploy -n
```

This will:
- Copy source files to a temporary deployment directory (`~/.tmp/deploy/`)
- Process ALL files for template replacement (replace `{{variables}}` with actual config values)
- Generate `services/.env` from configuration in the deployment copy
- Deploy the processed files from temp directory to `/home/ubuntu/services/` on the remote server
- Purge the destination folder before deployment to ensure a clean state
- Source files remain untouched with their template variables

> **Note**: Deployment always processes templates and deploys all services. Individual file updates should be done by editing source files and running a full deployment.

#### Restarting Services After Deployment

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

> **Note**: Configure `INFOMANIAK_TOKEN` in [`config/.env`](../../config/.env) for automatic DNS sync after infrastructure deployment. The DNS operations work on the `DOMAIN` (DNS zone) and will automatically find and update existing A/AAAA records for the specified subdomain. If records don't exist, they will be created automatically.

## Configuration Management

### Environment Variables
All configuration is managed through [`config/.env`](../../config/.env) which contains:
- OpenStack credentials for infrastructure
- Application settings and secrets
- Deployment configuration
- DNS and domain settings

### Template Processing
The deployment system processes template variables in ALL files:
- `{{VARIABLE_NAME}}` syntax is replaced with actual values
- Template processing happens during deployment
- Source files remain unchanged with template syntax

### Configuration Best Practices
1. **Never commit secrets**: Use the example config as a template
2. **Environment separation**: Use different configs for dev/staging/prod  
3. **Variable validation**: Check template processing with dry runs
4. **Backup configs**: Keep secure backups of production configurations

## Monitoring and Maintenance

### Application Health
```bash
# Check application status
box ssh "cd services && docker compose ps"

# View logs
box ssh "cd services && docker compose logs webapp"
box ssh "cd services && docker compose logs redis"
```

### Resource Monitoring
```bash
# Check server resources
box ssh "htop"
box ssh "df -h"
box ssh "free -h"
```

### Troubleshooting

#### Common Issues

**Deployment Failures:**
- Check template syntax with `box deploy -n`
- Verify SSH connectivity: `box ssh "echo test"`
- Check disk space: `box ssh "df -h"`

**Service Startup Issues:**
- Check logs: `box ssh "cd services && docker compose logs"`
- Verify configuration: `box ssh "cd services && cat .env"`
- Restart services: `box ssh "cd services && docker compose restart"`

**DNS Issues:**
- Verify Infomaniak token in config
- Check DNS propagation: `dig your-domain.com`
- Manual DNS update: `box dns update`

#### Backup and Recovery

**Configuration Backup:**
```bash
# Backup current configuration
cp config/.env config/.env.backup.$(date +%Y%m%d)
```

**Service Data Backup:**
```bash
# Backup Redis data
box ssh "cd services && docker compose exec redis redis-cli BGSAVE"
```

**Infrastructure Recovery:**
```bash
# Recreate infrastructure from code
box terraform plan
box terraform apply
```

## File Structure Reference

```
tapis-vert/
├── terraform/          # Infrastructure as code
│   ├── main.tf
│   ├── instances.tf
│   ├── network.tf
│   └── variables.tf
├── services/           # Application services
│   ├── compose.yml
│   ├── webapp/
│   ├── redis/
│   └── nginx/
├── box/               # Deployment environment
│   ├── box.sh
│   ├── compose.yml
│   └── opt/
└── config/
    └── .env           # Central configuration
```

## Security Considerations

### Infrastructure Security
- OpenStack security groups configured via Terraform
- SSH key-based authentication only
- Regular security updates via cloud-init

### Application Security
- Services run in isolated containers
- Redis protected by network isolation
- Nginx handles SSL termination

### Operational Security
- Configuration secrets stored securely
- SSH keys managed properly
- Access logging enabled

---

*For application development details, see the other documentation in this dev-ops section. For administrative tasks, see the [admin documentation](../admin/).* 