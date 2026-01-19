# Phase 1 Design Document: Linux Hardening & Endpoint Security

## Architecture Overview

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Control Node (Ansible)                    │
│  - Ansible 2.9+                                              │
│  - SSH key-based access to targets                           │
│  - Inventory management                                      │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        │ SSH/Ansible
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────┐              ┌───────▼────────┐
│  Target VM 1   │              │  Target VM 2   │
│  Ubuntu 22.04  │              │  Ubuntu 22.04  │
│  LTS Server    │              │  LTS Server    │
│                │              │                │
│  - SSH (22)    │              │  - SSH (22)    │
│  - UFW         │              │  - UFW         │
│  - fail2ban    │              │  - fail2ban    │
│  - auditd      │              │  - auditd      │
│  - AIDE        │              │  - AIDE        │
└────────────────┘              └────────────────┘
```

### Component Interactions
1. **Ansible Control Node** orchestrates hardening across target VMs
2. **Target VMs** receive hardening configurations via idempotent playbooks
3. **Validation Scripts** run locally on targets to collect evidence
4. **Lynis** performs security audits before and after hardening

## VM Layout

### Proxmox Host Configuration
- **Host OS**: Proxmox VE 7.x or 8.x
- **Network**: Isolated lab network (192.168.1.0/24 assumed)
- **Storage**: Local storage or NFS for VM images

### Target VM Specifications
- **OS**: Ubuntu 22.04 LTS Server (minimal installation)
- **CPU**: 2 vCPUs
- **RAM**: 2GB
- **Disk**: 20GB
- **Network**: Single NIC, static or DHCP
- **Initial Access**: SSH with password (will be hardened)

### Control Node Requirements
- **OS**: Any Linux/macOS with Ansible
- **Ansible**: 2.9+ (tested with 2.14+)
- **Python**: 3.8+
- **SSH Client**: Standard OpenSSH client
- **Network**: Access to target VM network

## Assumptions

### Security Assumptions
1. **Initial State**: Target VMs start with default Ubuntu 22.04 LTS configuration
2. **Network Isolation**: Lab environment is isolated from production
3. **Access Method**: Initial SSH access via password (will be hardened to key-only)
4. **Privileges**: Ansible user has sudo privileges on target hosts
5. **Backup Strategy**: SSH keys and critical configs are backed up before changes

### Operational Assumptions
1. **Maintenance Window**: Hardening can be performed during scheduled maintenance
2. **Rollback Capability**: Original configurations are backed up before changes
3. **Monitoring**: Basic system monitoring is in place (can be enhanced)
4. **Logging**: Local logging is sufficient (centralized logging is Phase 2+)

### Technical Assumptions
1. **Package Availability**: Standard Ubuntu repositories are accessible
2. **Time Synchronization**: NTP is configured (or will be configured)
3. **DNS Resolution**: Functional DNS for package installation
4. **Internet Access**: Required for package updates and security patches

## Success Criteria

### Functional Requirements
- [ ] All hardening playbooks execute successfully (idempotent)
- [ ] SSH access remains functional after hardening (key-based)
- [ ] Required services remain accessible after firewall configuration
- [ ] System remains stable after 24 hours of operation
- [ ] All validation scripts complete without errors

### Security Requirements
- [ ] Lynis security score improves by ≥15 points
- [ ] SSH password authentication is disabled
- [ ] Firewall allows only necessary ports
- [ ] fail2ban is active and monitoring SSH
- [ ] auditd is active and logging authentication events
- [ ] System is patched with latest security updates

### Operational Requirements
- [ ] Rollback playbook successfully restores baseline configuration
- [ ] All evidence files are generated and stored
- [ ] Documentation is complete and accurate
- [ ] Ansible playbooks are idempotent (can run multiple times safely)

### Evidence Requirements
- [ ] Baseline Lynis scan captured
- [ ] Post-hardening Lynis scan captured
- [ ] System configuration snapshots (before/after)
- [ ] Network service listings (before/after)
- [ ] SSH configuration (before/after)
- [ ] Firewall rules documented

## Risk Assessment

### Implementation Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| SSH lockout | High | Medium | Backup SSH keys, test access before disabling password auth |
| Service disruption | Medium | Low | Test firewall rules, maintain service allowlist |
| Configuration drift | Low | Medium | Use Ansible for idempotent configuration management |
| Performance degradation | Low | Low | Monitor system resources, tune auditd if needed |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Audit log overflow | Medium | Medium | Configure log rotation, monitor disk space |
| fail2ban false positives | Low | Low | Tune fail2ban thresholds, whitelist trusted IPs |
| Certificate expiration | Medium | Low | Monitor certificate validity, automate renewal |

## Deployment Strategy

### Phase 1: Preparation
1. Create target VMs in Proxmox
2. Install Ubuntu 22.04 LTS Server
3. Configure initial SSH access
4. Install Ansible on control node
5. Generate SSH key pair for Ansible

### Phase 2: Baseline
1. Run baseline assessment scripts
2. Capture Lynis baseline scan
3. Document initial system state
4. Backup critical configurations

### Phase 3: Hardening
1. Run Ansible hardening playbook
2. Verify SSH access remains functional
3. Test service accessibility
4. Monitor system logs for errors

### Phase 4: Validation
1. Run post-hardening validation scripts
2. Capture Lynis post-hardening scan
3. Compare baseline vs post-hardening
4. Document any issues or deviations

### Phase 5: Evidence Collection
1. Organize evidence files
2. Generate comparison reports
3. Document lessons learned
4. Update documentation

## Testing Strategy

### Unit Testing
- Ansible playbooks tested in isolated VM
- Validation scripts tested against known good/bad states
- PKI scripts tested with various certificate scenarios

### Integration Testing
- End-to-end hardening workflow tested
- Rollback procedure tested
- Evidence collection verified

### Regression Testing
- Idempotency verified (playbooks run multiple times)
- Configuration changes persist after reboot
- Services remain functional after hardening

## Monitoring & Alerting

### Post-Deployment Monitoring
- SSH access logs (fail2ban)
- Firewall rule effectiveness
- System resource usage (CPU, memory, disk)
- Audit log volume

### Alerting (Future Enhancement)
- SSH brute force attempts
- Unauthorized privilege escalation attempts
- Certificate expiration warnings
- System resource exhaustion

## Future Enhancements

### Phase 1+ Improvements
- Centralized logging (rsyslog/Syslog-NG)
- File integrity monitoring (AIDE) automation
- Automated certificate renewal
- Compliance reporting automation

### Integration with Later Phases
- SIEM integration (Phase 6)
- SOAR automation (Phase 7)
- Detection rules (Phase 8)
- Cloud security integration (Phase 4)
