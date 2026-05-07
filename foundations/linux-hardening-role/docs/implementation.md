# Implementation Guide

This guide is the deeper-dive companion to the role README — step-by-step commands, expected outputs, and troubleshooting for running the Linux hardening role end-to-end.

## Prerequisites

### Control Node Setup
1. Install Ansible 2.9+:
   ```bash
   # macOS
   brew install ansible
   
   # Ubuntu/Debian
   sudo apt update && sudo apt install ansible
   
   # Verify installation
   ansible --version
   ```

2. Generate SSH key pair (if not already done):
   ```bash
   ssh-keygen -t ed25519 -C "ansible-control-node"
   ```

3. Copy SSH public key to target hosts:
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub user@target-host
   ```

### Target Host Setup
1. Install Ubuntu 22.04 LTS Server
2. Configure network connectivity
3. Ensure sudo access for Ansible user
4. Install Python 3 (usually pre-installed):
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

## Step 1: Baseline Assessment

### Run Baseline Script
```bash
# From the role root (foundations/linux-hardening-role):
./scripts/baseline-assessment.sh <target-host>
```

Or for localhost:
```bash
./scripts/baseline-assessment.sh localhost
```

### Run Lynis Baseline
```bash
# Install Lynis (if not installed)
sudo apt install lynis

# Run baseline scan
sudo lynis audit system --profile /usr/share/lynis/default.prf > evidence/baseline/lynis-baseline.txt

# Review results
cat evidence/baseline/lynis-baseline.txt
```

### Review Baseline Evidence
```bash
ls -la evidence/baseline/
cat evidence/baseline/system-info.txt
cat evidence/baseline/ssh-config.txt
cat evidence/baseline/network-services.txt
```

## Step 2: Configure Ansible Inventory

### Edit Inventory File
```bash
cd ansible
nano inventory/hosts.yml
```

Update with your target host information:
```yaml
all:
  children:
    linux_servers:
      hosts:
        ubuntu-server-01:
          ansible_host: 203.0.113.10  # RFC 5737 docs range — replace with your target.
          ansible_user: ubuntu
          ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### Test Ansible Connection
```bash
ansible all -i inventory/hosts.yml -m ping
```

Expected output:
```
ubuntu-server-01 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## Step 3: Run Hardening Playbook

### Dry Run (Check Mode)
```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --check
```

This shows what would change without making changes.

### Apply Hardening
```bash
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
```

### Monitor Progress
The playbook will:
1. Backup critical configurations
2. Apply system updates
3. Harden SSH configuration
4. Configure firewall
5. Configure PAM
6. Set up auditd
7. Configure fail2ban
8. Apply system hardening

### Verify SSH Access Still Works
```bash
# Test SSH connection
ssh -i ~/.ssh/id_ed25519 user@target-host

# If connection fails, check:
# 1. SSH key is in authorized_keys
# 2. SSH service is running
# 3. Firewall allows SSH port
```

## Step 4: Post-Hardening Validation

### Run Validation Script
```bash
# From the role root (foundations/linux-hardening-role):
./scripts/post-hardening-validation.sh <target-host>
```

### Run Lynis Post-Hardening
```bash
sudo lynis audit system --profile /usr/share/lynis/default.prf > evidence/post/lynis-post.txt
```

### Compare Results
```bash
./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt
```

## Step 5: Manual Verification

### SSH Hardening
```bash
# Verify SSH config
sudo sshd -T | grep -E "(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication)"
# Expected: PasswordAuthentication no, PermitRootLogin no, PubkeyAuthentication yes

# Test SSH connection
ssh -v user@host
```

### Firewall
```bash
# Check UFW status
sudo ufw status verbose

# Verify listening ports
sudo netstat -tlnp | grep LISTEN
```

### fail2ban
```bash
# Check fail2ban status
sudo fail2ban-client status
sudo fail2ban-client status sshd

# View banned IPs
sudo fail2ban-client get sshd banned
```

### auditd
```bash
# Check auditd status
sudo systemctl status auditd

# View recent authentication events
sudo ausearch -m AUTH -i | tail -20
```

### System Updates
```bash
# Check update status
apt list --upgradable

# Verify unattended-upgrades
systemctl status unattended-upgrades
```

## Step 6: Evidence Collection

### Organize Evidence
```bash
cd evidence

# Baseline evidence
ls -la baseline/

# Post-hardening evidence
ls -la post/
```

### Generate Comparison Report
```bash
# Create comparison document
diff -u baseline/ssh-config.txt post/ssh-config.txt > post/ssh-config-diff.txt
diff -u baseline/network-services.txt post/network-services.txt > post/network-services-diff.txt
```

## Troubleshooting

### SSH Lockout
If you're locked out of SSH:

1. **Access via console** (Proxmox/VM console)
2. **Restore SSH config**:
   ```bash
   sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
   sudo systemctl restart sshd
   ```
3. **Verify SSH key is in authorized_keys**
4. **Re-run hardening playbook**

### Firewall Blocking Access
If services are blocked:

1. **Check firewall rules**:
   ```bash
   sudo ufw status verbose
   ```
2. **Temporarily allow service**:
   ```bash
   sudo ufw allow <port>/<protocol>
   ```
3. **Update inventory** with required ports
4. **Re-run firewall role**

### Ansible Connection Issues
```bash
# Test connectivity
ansible all -i inventory/hosts.yml -m ping

# Test with verbose output
ansible all -i inventory/hosts.yml -m ping -vvv

# Check SSH connection manually
ssh -i ~/.ssh/id_ed25519 user@target-host
```

### Playbook Failures
```bash
# Run with verbose output
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml -vvv

# Run specific role
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --tags ssh_hardening

# Check for syntax errors
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --syntax-check
```

## Rollback Procedure

### Automated Rollback
```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/rollback.yml
```

### Manual Rollback
See [README.md](../README.md#rollback) for manual rollback steps.

## Next Steps

After successful hardening:

1. **Document any deviations** from expected results
2. **Update inventory** with additional hosts
3. **Schedule regular validation** scans
4. **Set up monitoring** for:
   - fail2ban alerts
   - auditd log volume
   - Certificate expiration
5. **Iterate** the role as new CIS/Lynis findings surface in baseline scans.

## Best Practices

1. **Always test in non-production first**
2. **Maintain backups** of critical configurations
3. **Document customizations** for your environment
4. **Review evidence** regularly
5. **Keep playbooks updated** with latest security recommendations
6. **Use version control** for all configurations
