# Phase 1 — Linux Hardening & Endpoint Security

## Objective
Establish an enterprise-grade Linux security baseline aligned with CIS/NIST principles, emphasizing repeatability, auditability, and operational safety.

## Scope
- Ubuntu 22.04 LTS (Server)
- Proxmox-hosted virtual machines
- Automation via Ansible
- Validation via Lynis and system inspection

## Status
🚧 In Progress

This phase will include:
- Baseline assessment
- Automated hardening
- Validation and evidence
- PKI trust inspection
- Operational rollback considerations

---

## Threat Model (STRIDE)

### Spoofing
- **Risk**: Unauthorized access via compromised credentials or SSH key theft
- **Control**: SSH key-based auth, disable password auth, fail2ban

### Tampering
- **Risk**: Unauthorized modification of system files, logs, or configurations
- **Control**: File integrity monitoring (AIDE), auditd, immutable attributes

### Repudiation
- **Risk**: Attackers deny actions; lack of audit trail
- **Control**: Comprehensive auditd logging, centralized log aggregation

### Information Disclosure
- **Risk**: Sensitive data exposure via misconfigured services or weak permissions
- **Control**: Principle of least privilege, firewall allowlisting, service hardening

### Denial of Service
- **Risk**: Resource exhaustion via brute force or resource-intensive attacks
- **Control**: fail2ban, rate limiting, resource quotas

### Elevation of Privilege
- **Risk**: Unauthorized privilege escalation via misconfigured sudo or SUID binaries
- **Control**: PAM hardening, sudo restrictions, SUID audit

---

## Controls Mapping

| Control Domain | Implementation | Evidence |
|----------------|----------------|----------|
| **Access Control** | SSH hardening, PAM configuration, sudo restrictions | `evidence/post/ssh_config`, `evidence/post/pam_config` |
| **Network Security** | UFW firewall allowlisting, service hardening | `evidence/post/ufw_status`, `evidence/post/netstat` |
| **System Integrity** | AIDE baseline, auditd logging | `evidence/post/aide_check`, `evidence/post/auditd_status` |
| **Intrusion Prevention** | fail2ban configuration | `evidence/post/fail2ban_status` |
| **Patch Management** | Automated updates, security patches | `evidence/post/apt_upgrade` |
| **Audit & Logging** | auditd rules, syslog configuration | `evidence/post/auditd_rules` |

---

## Implementation

### Prerequisites
- Ansible 2.9+ installed on control node
- SSH access to target Ubuntu 22.04 LTS servers
- Sudo privileges on target hosts
- Network connectivity to target hosts

### Quick Start

1. **Baseline Assessment**
   ```bash
   # Run baseline checks
   ./scripts/baseline-assessment.sh <target-host>
   
   # Run Lynis baseline
   lynis audit system --profile /usr/share/lynis/default.prf > evidence/baseline/lynis-baseline.txt
   ```

2. **Run Hardening Playbook**
   ```bash
   cd ansible
   ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
   ```

3. **Post-Hardening Validation**
   ```bash
   # Run validation checks
   ./scripts/post-hardening-validation.sh <target-host>
   
   # Run Lynis post-hardening
   lynis audit system --profile /usr/share/lynis/default.prf > evidence/post/lynis-post.txt
   ```

### Detailed Steps

See [Implementation Guide](docs/implementation.md) for detailed walkthrough.

---

## Validation

### Automated Validation Scripts
- `scripts/baseline-assessment.sh` - Pre-hardening system state
- `scripts/post-hardening-validation.sh` - Post-hardening verification
- `scripts/compare-lynis.sh` - Compare baseline vs post-hardening Lynis scores

### Manual Validation Commands

#### SSH Hardening
```bash
# Verify SSH config
sudo sshd -T | grep -E "(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication)"
# Expected: PasswordAuthentication no, PermitRootLogin no, PubkeyAuthentication yes

# Test SSH connection
ssh -v user@host
```

#### Firewall Status
```bash
# Check UFW status
sudo ufw status verbose
# Expected: Status: active, only allowed ports listed

# Verify listening ports
sudo netstat -tlnp | grep LISTEN
# Expected: Only necessary services
```

#### fail2ban Status
```bash
# Check fail2ban status
sudo fail2ban-client status
sudo fail2ban-client status sshd
# Expected: Active jails with banned IPs if applicable
```

#### Audit Logging
```bash
# Check auditd status
sudo systemctl status auditd
sudo ausearch -m AUTH -i
# Expected: Active service, authentication events logged
```

#### System Updates
```bash
# Check update status
sudo apt list --upgradable
# Expected: Security updates applied
```

### Lynis Comparison
```bash
# Compare scores
./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt
# Expected: Score improvement, reduced warnings
```

---

## Evidence

### Baseline Evidence
- `evidence/baseline/lynis-baseline.txt` - Initial Lynis scan
- `evidence/baseline/system-info.txt` - System configuration snapshot
- `evidence/baseline/network-services.txt` - Listening services
- `evidence/baseline/ssh-config.txt` - SSH configuration

### Post-Hardening Evidence
- `evidence/post/lynis-post.txt` - Post-hardening Lynis scan
- `evidence/post/system-info.txt` - Hardened system state
- `evidence/post/network-services.txt` - Hardened service list
- `evidence/post/ssh-config.txt` - Hardened SSH config
- `evidence/post/ufw-status.txt` - Firewall rules
- `evidence/post/fail2ban-status.txt` - fail2ban status
- `evidence/post/auditd-status.txt` - Audit daemon status

---

## Rollback

### Automated Rollback
```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/rollback.yml
```

### Manual Rollback Steps

1. **SSH Configuration**
   ```bash
   sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
   sudo systemctl restart sshd
   ```

2. **Firewall Rules**
   ```bash
   sudo ufw --force reset
   sudo ufw default allow incoming
   sudo ufw enable
   ```

3. **fail2ban**
   ```bash
   sudo systemctl stop fail2ban
   sudo systemctl disable fail2ban
   ```

4. **Auditd**
   ```bash
   sudo systemctl stop auditd
   sudo systemctl disable auditd
   ```

### Rollback Verification
```bash
# Verify SSH access restored
ssh user@host

# Verify firewall reset
sudo ufw status
```

---

## PKI Trust Inspection

The PKI module provides tools for inspecting Linux trust stores and validating TLS certificates.

### Trust Store Inspection
```bash
# List system CA certificates
./pki/inspect-trust-store.sh

# Find certificate by subject
./pki/find-certificate.sh "CN=Example CA"
```

### TLS Chain Validation
```bash
# Validate remote TLS endpoint
./pki/validate-tls-chain.sh example.com:443

# Validate with custom CA bundle
./pki/validate-tls-chain.sh example.com:443 --ca-bundle /path/to/ca-bundle.pem
```

### Common Failure Cases
See [PKI Module Documentation](pki/README.md) for:
- Expired certificate detection
- Hostname mismatch validation
- Untrusted CA identification
- Certificate chain validation

---

## Lessons Learned

### Risk Reduction
- **SSH Hardening**: Eliminated password-based brute force attack surface
- **Firewall Allowlisting**: Reduced attack surface from ~65000 ports to <10
- **fail2ban**: Automated response to brute force attempts
- **Audit Logging**: Enabled forensic investigation capability

### Failure Modes
- **Lockout Risk**: SSH key loss can prevent access; maintain backup keys
- **Service Disruption**: Firewall misconfiguration can block legitimate traffic
- **Performance Impact**: Auditd can generate high log volume

### Detection & Monitoring
- **fail2ban**: Real-time brute force detection and blocking
- **auditd**: System call auditing for suspicious activity
- **Lynis**: Periodic security posture assessment

### Scale Implications
- **Ansible**: Scales to hundreds of hosts with minimal overhead
- **Centralized Logging**: Required for large deployments
- **Certificate Management**: Consider automation for large-scale PKI

### Operational Considerations
- **Change Windows**: Schedule hardening during maintenance windows
- **Testing**: Always test in non-production first
- **Documentation**: Maintain runbooks for common operations
- **Backup**: Ensure SSH keys and configurations are backed up

---

## References

- [CIS Ubuntu 22.04 LTS Benchmark](https://www.cisecurity.org/benchmark/ubuntu_linux)
- [NIST SP 800-53 Security Controls](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Lynis Documentation](https://cisofy.com/documentation/lynis/)

---

## Design Document

See [design/phase1-design.md](design/phase1-design.md) for architecture, VM layout, assumptions, and success criteria.

---

## Hardening Checklist

See [docs/hardening-checklist.md](docs/hardening-checklist.md) for the complete CIS/NIST-aligned hardening checklist.
