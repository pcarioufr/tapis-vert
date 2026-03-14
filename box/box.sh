#!/bin/bash

usage() {
    echo "----------------- box -----------------"
    echo "The Box: dev/ops/test toolbox for Tapis Vert."
    echo ""
    echo "Usage: box [-h] [-d] [--setup] [command]"
    echo ""
    echo "Options:"
    echo "    -h              show this help"
    echo "    -d              enable debug mode (verbose output)"
    echo "    --setup         check and install dependencies"
    echo ""
    echo "Commands:"
    echo "    deploy          deploy code to remote server (with template processing)"
    echo "    ssh             remote shell access and SSH key management"
    echo "    terraform       terraform wrapper (auto-exports credentials)"
    echo "    dns             manage DNS records via Infomaniak API"
    echo "    tunnel          SSH tunnel to admin interface or RedisInsight"
    echo "    test            integration test suite and database management"
    echo "    hello           smoke test (verify connectivity)"
    echo ""
    echo "Run 'box <command> -h' for detailed help on each command."
    echo ""
    echo "Examples:"
    echo "    box deploy                       # Full deployment"
    echo "    box deploy -p webapp             # Deploy only webapp/"
    echo "    box ssh                          # Open remote shell"
    echo "    box tunnel 8002:8002              # Admin at localhost:8002"
    echo "    box -d test init                 # Integration tests (debug)"
    echo "    box --setup                      # Install dependencies"
}

setup() {
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local RED='\033[0;31m'
    local NC='\033[0m'

    ok()           { echo -e "  ${GREEN}✓${NC} $1"; }
    installing()   { echo -e "  ${YELLOW}⟳${NC} Installing $1..."; }
    fail()         { echo -e "  ${RED}✗${NC} $1"; }

    echo ""
    echo "Tapis Vert — Setup"
    echo "==================="
    echo ""

    # --- Homebrew (required, not auto-installed) ---
    if ! command -v brew &> /dev/null; then
        fail "Homebrew is not installed."
        echo "    Install it from https://brew.sh/ then re-run this command."
        exit 1
    fi
    ok "Homebrew"

    # --- Docker Desktop ---
    if command -v docker &> /dev/null; then
        ok "Docker Desktop"
    else
        installing "Docker Desktop"
        brew install --cask docker-desktop
        ok "Docker Desktop installed — open Docker.app to complete setup"
    fi

    # --- Node.js ---
    if command -v node &> /dev/null; then
        ok "Node.js ($(node -v))"
    else
        installing "Node.js"
        brew install node
        ok "Node.js ($(node -v))"
    fi

    # --- Terraform ---
    if command -v terraform &> /dev/null; then
        ok "Terraform ($(terraform -v | head -1 | awk '{print $2}'))"
    else
        installing "Terraform"
        brew install terraform
        ok "Terraform ($(terraform -v | head -1 | awk '{print $2}'))"
    fi

    # --- agent-browser ---
    if command -v agent-browser &> /dev/null; then
        ok "agent-browser"
    else
        installing "agent-browser"
        brew install agent-browser
        ok "agent-browser"
    fi

    # --- agent-browser Claude skill ---
    local SKILL_DIR="$HOME/.claude/skills/agent-browser"
    if [ -d "$SKILL_DIR" ]; then
        ok "agent-browser Claude skill"
    else
        installing "agent-browser Claude skill"
        npx -y skills add -y vercel-labs/agent-browser agent-browser
        ok "agent-browser Claude skill"
    fi

    echo ""
    echo -e "${GREEN}Done.${NC} Run 'box -h' for available commands."
    echo ""
}

# Handle --setup before getopts (which doesn't support long options)
if [ "$1" = "--setup" ]; then
    setup
    exit 0
fi

while getopts "hd" option; do
case ${option} in
    h) usage && exit 0 ;;
    d)
        export DEBUG=1
        echo "debug mode enabled"
        ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

BOX_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "${BOX_DIR}")"

CMD="${1:-}"

if [ -z "${CMD}" ]; then
    usage
    exit 0
fi

if [ ! -f "${BOX_DIR}/cmd/${CMD}.sh" ]; then
    echo "Unknown command: ${CMD}"
    usage
    exit 1
fi

shift

# Export BOX_REPO_ROOT so scripts can resolve paths (libs, config, data)
export BOX_REPO_ROOT="${REPO_ROOT}"

# Source shared libs (debug, success, error, etc.)
for f in "${BOX_DIR}/libs/"* ; do source "$f"; done

# Load and export config
if [ -f "${REPO_ROOT}/config/.env" ]; then
    set -a
    source "${REPO_ROOT}/config/.env"
    export SSH_HOST="${DEPLOY_USER}@${SUBDOMAIN}.${DOMAIN}"
    export SSH_KEY="$HOME/.ssh/id_rsa"
    set +a
else
    echo "Config file ${REPO_ROOT}/config/.env not found"
    exit 1
fi

source "${BOX_DIR}/cmd/${CMD}.sh" "$@"
