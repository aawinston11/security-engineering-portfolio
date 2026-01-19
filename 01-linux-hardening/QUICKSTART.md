# Quick Start Guide

Get started with Phase 1 Linux Hardening in 5 minutes.

## Prerequisites Check

```bash
# Check Ansible
ansible --version  # Should be 2.9+

# Check SSH access
ssh user@target-host  # Should work without password (key-based)

# Check Python on target
ssh user@target-host "python3 --version"  # Should be 3.8+
```

## 5-Minute Setup

### 1. Configure Inventory (1 min)
```bash
cd 01-linux-hardening/ansible
nano inventory/hosts.yml
# Update with your target host IP and user
```

### 2. Test Connection (30 sec)
```bash
ansible all -i inventory/hosts.yml -m ping
```

### 3. Run Baseline (1 min)
```bash
cd ..
./scripts/baseline-assessment.sh <target-host>
```

### 4. Run Hardening (2 min)
```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
```

### 5. Validate (30 sec)
```bash
cd ..
./scripts/post-hardening-validation.sh <target-host>
```

## Expected Results

After hardening, you should see:
- ✓ SSH password auth disabled
- ✓ Firewall active
- ✓ fail2ban running
- ✓ auditd logging
- ✓ System updates configured

## Next Steps

1. Review evidence in `evidence/post/`
2. Run Lynis scans (baseline and post-hardening)
3. Compare results: `./scripts/compare-lynis.sh`
4. Review [README.md](README.md) for detailed documentation

## Troubleshooting

**SSH lockout?** See [Rollback](README.md#rollback) section.

**Playbook fails?** Run with `-vvv` for verbose output.

**Need help?** See [Implementation Guide](docs/implementation.md).
