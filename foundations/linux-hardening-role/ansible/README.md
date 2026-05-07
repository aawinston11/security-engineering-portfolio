# Ansible Hardening Implementation

This directory contains the Ansible playbooks and roles for automating Linux hardening.

## Structure

```
ansible/
├── ansible.cfg          # Ansible configuration
├── inventory/           # Host inventory
│   └── hosts.yml        # Example inventory file
├── playbooks/           # Main playbooks
│   ├── harden.yml       # Main hardening playbook
│   └── rollback.yml     # Rollback playbook
└── roles/               # Ansible roles
    ├── system_updates/  # System updates and patching
    ├── ssh_hardening/   # SSH configuration hardening
    ├── firewall/        # UFW firewall configuration
    ├── pam_config/      # PAM authentication configuration
    ├── auditd_config/   # Audit logging configuration
    ├── fail2ban_config/ # Intrusion prevention
    └── system_hardening/# Kernel and system hardening
```

## Quick Start

### 1. Configure Inventory

Edit `inventory/hosts.yml` with your target hosts:

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

### 2. Test Connection

```bash
ansible all -i inventory/hosts.yml -m ping
```

### 3. Run Hardening Playbook

```bash
# Dry run (check mode)
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --check

# Apply hardening
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
```

### 4. Rollback (if needed)

```bash
ansible-playbook -i inventory/hosts.yml playbooks/rollback.yml
```

## Roles

### system_updates
- Configures automatic security updates
- Installs and configures unattended-upgrades
- Applies security patches

### ssh_hardening
- Disables password authentication
- Disables root login
- Enables key-based authentication
- Configures SSH security settings

### firewall
- Installs and configures UFW
- Sets default deny policies
- Allows only necessary ports

### pam_config
- Configures password complexity
- Sets up account lockout
- Configures secure umask

### auditd_config
- Installs and configures auditd
- Sets up audit rules for:
  - Authentication events
  - File system changes
  - Privilege escalation
  - System time changes

### fail2ban_config
- Installs and configures fail2ban
- Sets up SSH jail
- Configures ban times and thresholds

### system_hardening
- Configures kernel parameters
- Hardens network settings
- Configures /tmp and /var/tmp security

## Variables

Key variables can be set in inventory or playbook:

```yaml
ssh_port: 22
ssh_allowed_users: "{{ ansible_user }}"
fail2ban_ban_time: 3600
fail2ban_findtime: 600
fail2ban_maxretry: 3
allowed_ports:
  - port: 22
    protocol: tcp
    comment: "SSH access"
```

## Idempotency

All playbooks and roles are designed to be idempotent. You can run them multiple times safely:

```bash
# Safe to run multiple times
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
```

## Best Practices

1. **Always test in check mode first**: `--check`
2. **Use version control**: Commit playbooks and inventory (without secrets)
3. **Backup before changes**: Playbooks create backups automatically
4. **Test rollback**: Verify rollback procedure works
5. **Document customizations**: Note any environment-specific changes

## Troubleshooting

### Connection Issues
```bash
# Test with verbose output
ansible all -i inventory/hosts.yml -m ping -vvv

# Test SSH manually
ssh -i ~/.ssh/id_ed25519 user@target-host
```

### Playbook Failures
```bash
# Run with verbose output
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml -vvv

# Run specific role
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --tags ssh_hardening
```

### Syntax Errors
```bash
# Check syntax
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --syntax-check
```

## References

- [Ansible Documentation](https://docs.ansible.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [CIS Ubuntu 22.04 Benchmark](https://www.cisecurity.org/benchmark/ubuntu_linux)
