#!/bin/bash

set -e

# Simple Docker orchestration script
# All test logic is handled by Python in the container

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Parse command line arguments
REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --rebuild    Force rebuild of Docker images"
            echo "  --help       Show this help message"
            echo ""
            echo "This script runs Redis ORM tests using Docker."
            echo "All test logic and output formatting is handled by Python."
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

print_info "🚀 Redis ORM Test Suite"
echo "======================="
echo ""

# Cleanup any existing containers
print_info "Cleaning up existing test containers..."
docker compose -f compose.yml down --volumes --remove-orphans 2>/dev/null || true

# Build containers
if [ "$REBUILD" = true ]; then
    print_info "Building Docker containers (--no-cache)..."
    docker compose -f compose.yml build --no-cache
else
    print_info "Building Docker containers..."
    docker compose -f compose.yml build
fi

# Run tests (all logic is in Python)
print_info "Starting test containers..."
print_info "Test execution and logging handled by Python..."
echo ""

# Run the test suite
if docker compose -f compose.yml up --abort-on-container-exit python-tests; then
    print_success "🎉 Test suite completed!"
    exit_code=0
else
    print_error "❌ Test suite failed!"
    echo ""
    print_warning "🔧 Debugging Information:"
    echo "     docker compose -f compose.yml logs redis"
    echo "     docker compose -f compose.yml logs python-tests"  
    echo "     docker compose -f compose.yml run python-tests bash"
    exit_code=1
fi

# Cleanup
print_info "Cleaning up test containers..."
docker compose -f compose.yml down --volumes --remove-orphans 2>/dev/null || true

exit $exit_code 