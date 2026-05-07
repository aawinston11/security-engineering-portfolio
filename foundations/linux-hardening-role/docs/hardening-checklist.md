# CIS/NIST-Aligned Hardening Checklist for Ubuntu 22.04 LTS

This checklist aligns with CIS Ubuntu 22.04 LTS Benchmark and NIST SP 800-53 controls.

## 1. System Updates & Patching

### 1.1 Automated Security Updates
- [ ] Configure automatic security updates via `unattended-upgrades`
- [ ] Enable automatic reboot for security updates (optional, requires maintenance window)
- [ ] Verify update sources are configured correctly
- [ ] Test update mechanism

**NIST Control**: SI-2 (Flaw Remediation)  
**CIS Benchmark**: 1.1.1.1 - 1.1.1.4

### 1.2 Package Management
- [ ] Remove unnecessary packages
- [ ] Verify package integrity (apt-secure)
- [ ] Configure package source authentication

**NIST Control**: CM-7 (Least Functionality)  
**CIS Benchmark**: 1.1.2 - 1.1.3

## 2. SSH Hardening

### 2.1 SSH Configuration
- [ ] Disable root login (`PermitRootLogin no`)
- [ ] Disable password authentication (`PasswordAuthentication no`)
- [ ] Enable public key authentication (`PubkeyAuthentication yes`)
- [ ] Set protocol version to 2 (`Protocol 2`)
- [ ] Disable X11 forwarding (`X11Forwarding no`)
- [ ] Set maximum authentication attempts (`MaxAuthTries 3`)
- [ ] Set client alive interval (`ClientAliveInterval 300`)
- [ ] Set client alive count max (`ClientAliveCountMax 2`)
- [ ] Disable empty passwords (`PermitEmptyPasswords no`)
- [ ] Set banner message (`Banner /etc/issue.net`)

**NIST Control**: AC-17 (Remote Access), IA-2 (Identification and Authentication)  
**CIS Benchmark**: 5.2.1 - 5.2.22

### 2.2 SSH Key Management
- [ ] Generate strong SSH key pairs (RSA 4096 or Ed25519)
- [ ] Secure private key storage (600 permissions)
- [ ] Configure authorized_keys with proper permissions
- [ ] Implement key rotation policy
- [ ] Backup SSH keys securely

**NIST Control**: IA-5 (Authenticator Management)  
**CIS Benchmark**: 5.2.8

## 3. Firewall Configuration

### 3.1 UFW (Uncomplicated Firewall)
- [ ] Install and enable UFW
- [ ] Set default policies (deny incoming, allow outgoing)
- [ ] Allow only necessary ports (SSH, application-specific)
- [ ] Configure rate limiting for SSH
- [ ] Log firewall events
- [ ] Verify firewall is active and persistent

**NIST Control**: SC-7 (Boundary Protection)  
**CIS Benchmark**: 3.5.1 - 3.5.2

### 3.2 Service Hardening
- [ ] Disable unnecessary network services
- [ ] Verify only required services are listening
- [ ] Configure service-specific firewall rules
- [ ] Review listening ports regularly

**NIST Control**: CM-7 (Least Functionality)  
**CIS Benchmark**: 2.1.1 - 2.1.22

## 4. PAM (Pluggable Authentication Modules)

### 4.1 Password Policy
- [ ] Configure password complexity requirements
- [ ] Set password aging policies
- [ ] Configure password history
- [ ] Set account lockout policy

**NIST Control**: IA-5 (Authenticator Management)  
**CIS Benchmark**: 5.4.1 - 5.4.4

### 4.2 PAM Configuration
- [ ] Configure `pam_tally2` or `pam_faillock` for account lockout
- [ ] Set secure umask (027)
- [ ] Configure session management
- [ ] Review PAM module configuration

**NIST Control**: AC-7 (Unsuccessful Logon Attempts)  
**CIS Benchmark**: 5.3.1 - 5.3.4

## 5. Audit Logging

### 5.1 auditd Configuration
- [ ] Install and enable auditd
- [ ] Configure audit rules for:
  - Authentication events
  - File system changes
  - Network connections
  - Privilege escalation
  - System calls
- [ ] Set audit log retention policy
- [ ] Configure log rotation
- [ ] Monitor audit log disk usage

**NIST Control**: AU-2 (Audit Events), AU-3 (Content of Audit Records)  
**CIS Benchmark**: 4.1.1 - 4.1.18

### 5.2 Log Management
- [ ] Configure rsyslog for centralized logging (optional)
- [ ] Set log file permissions (640)
- [ ] Configure log rotation
- [ ] Monitor log disk usage
- [ ] Implement log retention policy

**NIST Control**: AU-4 (Audit Storage Capacity), AU-9 (Protection of Audit Information)  
**CIS Benchmark**: 4.2.1 - 4.2.4

## 6. Intrusion Prevention

### 6.1 fail2ban Configuration
- [ ] Install and enable fail2ban
- [ ] Configure SSH jail with appropriate ban time
- [ ] Set findtime and maxretry thresholds
- [ ] Configure email notifications (optional)
- [ ] Whitelist trusted IP addresses
- [ ] Test fail2ban functionality
- [ ] Monitor fail2ban logs

**NIST Control**: SI-4 (System Monitoring), SC-7 (Boundary Protection)  
**CIS Benchmark**: 3.4.1 - 3.4.2

### 6.2 File Integrity Monitoring
- [ ] Install AIDE (Advanced Intrusion Detection Environment)
- [ ] Initialize AIDE database
- [ ] Configure AIDE rules
- [ ] Schedule regular integrity checks
- [ ] Document baseline database location
- [ ] Test AIDE functionality

**NIST Control**: SI-7 (Software, Firmware, and Information Integrity)  
**CIS Benchmark**: 1.4.1 - 1.4.2

## 7. System Hardening

### 7.1 Kernel Parameters
- [ ] Disable IP forwarding (if not needed)
- [ ] Disable source routing
- [ ] Configure SYN flood protection
- [ ] Set ICMP redirect acceptance
- [ ] Configure secure ICMP handling

**NIST Control**: SC-7 (Boundary Protection)  
**CIS Benchmark**: 3.3.1 - 3.3.9

### 7.2 File System Security
- [ ] Configure /tmp with noexec, nosuid
- [ ] Configure /var/tmp with noexec, nosuid
- [ ] Configure /home with nosuid (if applicable)
- [ ] Set sticky bit on world-writable directories
- [ ] Review SUID/SGID binaries

**NIST Control**: CM-7 (Least Functionality)  
**CIS Benchmark**: 1.1.14 - 1.1.22

### 7.3 User Management
- [ ] Remove default users (if present)
- [ ] Disable unused accounts
- [ ] Configure user account restrictions
- [ ] Set secure umask for users
- [ ] Review sudoers configuration

**NIST Control**: AC-2 (Account Management), AC-3 (Access Enforcement)  
**CIS Benchmark**: 5.4.1 - 5.4.5

## 8. Network Security

### 8.1 Network Configuration
- [ ] Disable unnecessary network protocols
- [ ] Configure secure network time synchronization (NTP)
- [ ] Disable IPv6 if not needed
- [ ] Configure secure DNS resolution

**NIST Control**: SC-7 (Boundary Protection), AU-8 (Time Stamps)  
**CIS Benchmark**: 3.1.1 - 3.1.2

### 8.2 TCP Wrappers
- [ ] Configure /etc/hosts.allow and /etc/hosts.deny
- [ ] Restrict service access via TCP wrappers
- [ ] Test TCP wrapper rules

**NIST Control**: AC-17 (Remote Access)  
**CIS Benchmark**: 3.4.3 - 3.4.4

## 9. Application Security

### 9.1 Service Configuration
- [ ] Review and harden web server configuration (if applicable)
- [ ] Review and harden database configuration (if applicable)
- [ ] Configure service-specific security settings
- [ ] Remove default configurations

**NIST Control**: CM-7 (Least Functionality)  
**CIS Benchmark**: Application-specific

## 10. Compliance & Validation

### 10.1 Security Scanning
- [ ] Run Lynis security audit (baseline)
- [ ] Run Lynis security audit (post-hardening)
- [ ] Compare scores and address findings
- [ ] Document remediation actions

**NIST Control**: CA-2 (Security Assessments)  
**CIS Benchmark**: All sections

### 10.2 Documentation
- [ ] Document all configuration changes
- [ ] Maintain change log
- [ ] Document rollback procedures
- [ ] Create operational runbooks

**NIST Control**: CM-3 (Configuration Change Control)  
**CIS Benchmark**: Documentation

## Implementation Priority

### Critical (Implement First)
1. System updates and patching
2. SSH hardening
3. Firewall configuration
4. fail2ban installation

### High Priority
5. Audit logging (auditd)
6. PAM configuration
7. File integrity monitoring (AIDE)

### Medium Priority
8. Kernel parameter tuning
9. File system security
10. Network security hardening

### Low Priority (Optional)
11. TCP wrappers
12. Advanced service hardening
13. Compliance reporting automation

## Validation Commands

### Verify Updates
```bash
sudo apt list --upgradable
sudo unattended-upgrades --dry-run
```

### Verify SSH
```bash
sudo sshd -T | grep -E "(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication)"
```

### Verify Firewall
```bash
sudo ufw status verbose
sudo netstat -tlnp
```

### Verify fail2ban
```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

### Verify auditd
```bash
sudo systemctl status auditd
sudo ausearch -m AUTH -i
```

### Verify AIDE
```bash
sudo aide --check
```
