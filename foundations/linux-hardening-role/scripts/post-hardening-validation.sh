#!/bin/bash
# Post-Hardening Validation Script
# Validates hardening implementation and collects evidence

set -euo pipefail

TARGET_HOST="${1:-localhost}"
EVIDENCE_DIR="$(dirname "$0")/../evidence/post"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create evidence directory if it doesn't exist
mkdir -p "$EVIDENCE_DIR"

echo "=== Post-Hardening Validation for $TARGET_HOST ==="
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

# Function to check command output
check_cmd() {
    local cmd="$1"
    local expected="$2"
    local description="$3"
    
    echo -n "Checking: $description... "
    
    if [ "$TARGET_HOST" != "localhost" ]; then
        result=$(ssh "$TARGET_HOST" "$cmd" 2>/dev/null || echo "FAILED")
    else
        result=$(eval "$cmd" 2>/dev/null || echo "FAILED")
    fi
    
    if echo "$result" | grep -q "$expected"; then
        echo "✓ PASS"
        return 0
    else
        echo "✗ FAIL (got: $result)"
        return 1
    fi
}

FAILED_CHECKS=0

# System Information
echo "[1/10] Collecting system information..."
run_cmd "uname -a && hostname && cat /etc/os-release" "$EVIDENCE_DIR/system-info-${TIMESTAMP}.txt"

# SSH Configuration Validation
echo "[2/10] Validating SSH configuration..."
run_cmd "sudo sshd -T" "$EVIDENCE_DIR/ssh-config-${TIMESTAMP}.txt"

check_cmd "sudo sshd -T | grep -E '^passwordauthentication'" "no" "SSH password authentication disabled" || ((FAILED_CHECKS++))
check_cmd "sudo sshd -T | grep -E '^permitrootlogin'" "no" "SSH root login disabled" || ((FAILED_CHECKS++))
check_cmd "sudo sshd -T | grep -E '^pubkeyauthentication'" "yes" "SSH public key authentication enabled" || ((FAILED_CHECKS++))

# Firewall Validation
echo "[3/10] Validating firewall configuration..."
run_cmd "sudo ufw status verbose" "$EVIDENCE_DIR/ufw-status-${TIMESTAMP}.txt"

check_cmd "sudo ufw status | head -1" "Status: active" "UFW firewall active" || ((FAILED_CHECKS++))
check_cmd "sudo ufw status | grep -E '^22.*ALLOW'" "22" "SSH port allowed" || ((FAILED_CHECKS++))

# Network Services
echo "[4/10] Collecting network services..."
run_cmd "sudo netstat -tlnp 2>/dev/null || sudo ss -tlnp" "$EVIDENCE_DIR/network-services-${TIMESTAMP}.txt"

# fail2ban Validation
echo "[5/10] Validating fail2ban..."
run_cmd "sudo fail2ban-client status 2>/dev/null || echo 'fail2ban not running'" "$EVIDENCE_DIR/fail2ban-status-${TIMESTAMP}.txt"

check_cmd "sudo systemctl is-active fail2ban 2>/dev/null || echo 'inactive'" "active" "fail2ban service active" || ((FAILED_CHECKS++))

# auditd Validation
echo "[6/10] Validating auditd..."
run_cmd "sudo systemctl status auditd --no-pager 2>/dev/null || echo 'auditd not running'" "$EVIDENCE_DIR/auditd-status-${TIMESTAMP}.txt"

check_cmd "sudo systemctl is-active auditd 2>/dev/null || echo 'inactive'" "active" "auditd service active" || ((FAILED_CHECKS++))

# System Updates
echo "[7/10] Checking system updates..."
run_cmd "apt list --upgradable 2>/dev/null" "$EVIDENCE_DIR/updates-${TIMESTAMP}.txt"
run_cmd "systemctl is-enabled unattended-upgrades 2>/dev/null || echo 'disabled'" "$EVIDENCE_DIR/unattended-upgrades-${TIMESTAMP}.txt"

# PAM Configuration
echo "[8/10] Validating PAM configuration..."
run_cmd "cat /etc/pam.d/common-password /etc/pam.d/common-auth 2>/dev/null" "$EVIDENCE_DIR/pam-config-${TIMESTAMP}.txt"

check_cmd "grep -q 'pam_pwquality' /etc/pam.d/common-password 2>/dev/null && echo 'found' || echo 'not found'" "found" "PAM password quality configured" || ((FAILED_CHECKS++))

# Kernel Parameters
echo "[9/10] Validating kernel parameters..."
run_cmd "sysctl -a 2>/dev/null | grep -E '(ip_forward|send_redirects|accept_redirects|icmp|tcp_syncookies)'" "$EVIDENCE_DIR/kernel-params-${TIMESTAMP}.txt"

check_cmd "sysctl net.ipv4.ip_forward 2>/dev/null" "0" "IP forwarding disabled" || ((FAILED_CHECKS++))
check_cmd "sysctl net.ipv4.tcp_syncookies 2>/dev/null" "1" "TCP SYN cookies enabled" || ((FAILED_CHECKS++))

# File System Security
echo "[10/10] Validating file system security..."
run_cmd "mount | grep -E '(tmp|var/tmp)'" "$EVIDENCE_DIR/filesystem-${TIMESTAMP}.txt"

# Create symlinks for latest
for file in "$EVIDENCE_DIR"/*-${TIMESTAMP}.txt; do
    basename_file=$(basename "$file" "-${TIMESTAMP}.txt")
    ln -sf "$(basename "$file")" "$EVIDENCE_DIR/${basename_file}.txt" 2>/dev/null || true
done

echo ""
echo "=== Post-Hardening Validation Complete ==="
echo "Evidence files saved to: $EVIDENCE_DIR"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✓ All validation checks PASSED"
    echo ""
    echo "Next steps:"
    echo "1. Run Lynis post-hardening: lynis audit system > $EVIDENCE_DIR/lynis-post.txt"
    echo "2. Compare with baseline: ./scripts/compare-lynis.sh"
    exit 0
else
    echo "✗ $FAILED_CHECKS validation check(s) FAILED"
    echo "Review evidence files and hardening playbook"
    exit 1
fi
