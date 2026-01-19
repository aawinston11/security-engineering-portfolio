#!/bin/bash
# Baseline Assessment Script
# Collects pre-hardening system state for comparison

set -euo pipefail

TARGET_HOST="${1:-localhost}"
EVIDENCE_DIR="$(dirname "$0")/../evidence/baseline"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create evidence directory if it doesn't exist
mkdir -p "$EVIDENCE_DIR"

echo "=== Baseline Assessment for $TARGET_HOST ==="
echo "Evidence will be saved to: $EVIDENCE_DIR"
echo ""

# Function to run command remotely or locally
run_cmd() {
    local cmd="$1"
    local output_file="$2"
    
    if [ "$TARGET_HOST" != "localhost" ]; then
        ssh "$TARGET_HOST" "$cmd" > "$output_file" 2>&1 || true
    else
        eval "$cmd" > "$output_file" 2>&1 || true
    fi
}

# System Information
echo "[1/8] Collecting system information..."
run_cmd "uname -a && hostname && cat /etc/os-release" "$EVIDENCE_DIR/system-info-${TIMESTAMP}.txt"

# SSH Configuration
echo "[2/8] Collecting SSH configuration..."
run_cmd "sudo cat /etc/ssh/sshd_config" "$EVIDENCE_DIR/ssh-config-${TIMESTAMP}.txt"

# Network Services
echo "[3/8] Collecting network services..."
run_cmd "sudo netstat -tlnp 2>/dev/null || sudo ss -tlnp" "$EVIDENCE_DIR/network-services-${TIMESTAMP}.txt"

# Firewall Status
echo "[4/8] Collecting firewall status..."
run_cmd "sudo ufw status verbose 2>/dev/null || echo 'UFW not installed'" "$EVIDENCE_DIR/ufw-status-${TIMESTAMP}.txt"

# Installed Packages
echo "[5/8] Collecting installed packages..."
run_cmd "dpkg -l | grep -E '(ssh|ufw|fail2ban|audit)'" "$EVIDENCE_DIR/packages-${TIMESTAMP}.txt"

# System Updates
echo "[6/8] Checking system updates..."
run_cmd "apt list --upgradable 2>/dev/null" "$EVIDENCE_DIR/updates-${TIMESTAMP}.txt"

# PAM Configuration
echo "[7/8] Collecting PAM configuration..."
run_cmd "cat /etc/pam.d/common-password /etc/pam.d/common-auth 2>/dev/null" "$EVIDENCE_DIR/pam-config-${TIMESTAMP}.txt"

# Kernel Parameters
echo "[8/8] Collecting kernel parameters..."
run_cmd "sysctl -a 2>/dev/null | grep -E '(ip_forward|send_redirects|accept_redirects|icmp|tcp_syncookies)'" "$EVIDENCE_DIR/kernel-params-${TIMESTAMP}.txt"

# Create symlinks for latest
for file in "$EVIDENCE_DIR"/*-${TIMESTAMP}.txt; do
    basename_file=$(basename "$file" "-${TIMESTAMP}.txt")
    ln -sf "$(basename "$file")" "$EVIDENCE_DIR/${basename_file}.txt" 2>/dev/null || true
done

echo ""
echo "=== Baseline Assessment Complete ==="
echo "Evidence files saved to: $EVIDENCE_DIR"
echo ""
echo "Next steps:"
echo "1. Review evidence files"
echo "2. Run Lynis baseline: lynis audit system > $EVIDENCE_DIR/lynis-baseline.txt"
echo "3. Proceed with hardening: cd ansible && ansible-playbook -i inventory/hosts.yml playbooks/harden.yml"
