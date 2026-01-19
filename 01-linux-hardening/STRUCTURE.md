# Phase 1 Repository Structure

Complete file structure and purpose of each component.

## Directory Tree

```
01-linux-hardening/
├── README.md                    # Main documentation (enterprise-style)
├── QUICKSTART.md                # 5-minute quick start guide
├── STRUCTURE.md                 # This file - structure overview
├── .gitignore                   # Git ignore rules
│
├── design/                      # Design documents
│   └── phase1-design.md        # Architecture, VM layout, assumptions, success criteria
│
├── docs/                        # Documentation
│   ├── hardening-checklist.md  # CIS/NIST-aligned checklist
│   └── implementation.md       # Step-by-step implementation guide
│
├── ansible/                     # Ansible automation
│   ├── README.md               # Ansible-specific documentation
│   ├── ansible.cfg             # Ansible configuration
│   │
│   ├── inventory/              # Host inventory
│   │   └── hosts.yml           # Example inventory file
│   │
│   ├── playbooks/              # Main playbooks
│   │   ├── harden.yml         # Main hardening playbook
│   │   └── rollback.yml       # Rollback playbook
│   │
│   └── roles/                  # Ansible roles (modular)
│       ├── system_updates/     # System updates & patching
│       ├── ssh_hardening/      # SSH configuration
│       ├── firewall/           # UFW firewall
│       ├── pam_config/          # PAM authentication
│       ├── auditd_config/       # Audit logging
│       ├── fail2ban_config/     # Intrusion prevention
│       └── system_hardening/    # Kernel & system hardening
│
├── scripts/                     # Validation & assessment scripts
│   ├── baseline-assessment.sh  # Pre-hardening system state
│   ├── post-hardening-validation.sh  # Post-hardening verification
│   └── compare-lynis.sh        # Compare Lynis scans
│
├── pki/                         # PKI trust inspection module
│   ├── README.md               # PKI module documentation
│   ├── inspect-trust-store.sh  # List system CA certificates
│   ├── find-certificate.sh     # Find certificate by subject/issuer
│   └── validate-tls-chain.sh  # Validate TLS certificate chain
│
└── evidence/                    # Evidence collection
    ├── baseline/               # Pre-hardening evidence
    │   └── .gitkeep
    └── post/                   # Post-hardening evidence
        └── .gitkeep
```

## File Purposes

### Documentation
- **README.md**: Main entry point with all enterprise sections (threat model, controls, validation, rollback, lessons learned)
- **QUICKSTART.md**: Fast-track guide for experienced users
- **STRUCTURE.md**: This file - repository structure overview
- **design/phase1-design.md**: Architecture, assumptions, success criteria
- **docs/hardening-checklist.md**: Complete CIS/NIST checklist
- **docs/implementation.md**: Detailed step-by-step guide

### Automation
- **ansible/playbooks/harden.yml**: Main hardening playbook (orchestrates all roles)
- **ansible/playbooks/rollback.yml**: Rollback playbook to restore baseline
- **ansible/roles/**: Modular roles for each hardening domain
- **ansible/inventory/hosts.yml**: Target host inventory
- **ansible/ansible.cfg**: Ansible configuration

### Validation
- **scripts/baseline-assessment.sh**: Collects pre-hardening state
- **scripts/post-hardening-validation.sh**: Validates hardening implementation
- **scripts/compare-lynis.sh**: Compares baseline vs post-hardening Lynis scores

### PKI Module
- **pki/inspect-trust-store.sh**: Lists system CA certificates
- **pki/find-certificate.sh**: Searches trust store
- **pki/validate-tls-chain.sh**: Validates remote TLS endpoints

### Evidence
- **evidence/baseline/**: Pre-hardening system snapshots
- **evidence/post/**: Post-hardening validation results

## Workflow

### 1. Planning
- Read `README.md` for overview
- Review `design/phase1-design.md` for architecture
- Check `docs/hardening-checklist.md` for requirements

### 2. Preparation
- Configure `ansible/inventory/hosts.yml`
- Test Ansible connectivity
- Review `docs/implementation.md`

### 3. Baseline
- Run `scripts/baseline-assessment.sh`
- Run Lynis baseline scan
- Review evidence in `evidence/baseline/`

### 4. Hardening
- Run `ansible/playbooks/harden.yml`
- Monitor playbook execution
- Verify SSH access still works

### 5. Validation
- Run `scripts/post-hardening-validation.sh`
- Run Lynis post-hardening scan
- Compare with baseline using `scripts/compare-lynis.sh`

### 6. Evidence
- Review evidence in `evidence/post/`
- Document any deviations
- Update documentation as needed

## Key Features

### Enterprise-Grade
- ✅ Idempotent automation (safe to run multiple times)
- ✅ Rollback capability
- ✅ Evidence collection
- ✅ Comprehensive validation
- ✅ Threat model and controls mapping

### Interview-Ready
- ✅ Risk reduction documentation
- ✅ Failure mode analysis
- ✅ Detection and monitoring
- ✅ Scale implications
- ✅ Operational considerations

### Production-Ready
- ✅ Backup before changes
- ✅ Validation scripts
- ✅ Error handling
- ✅ Detailed logging
- ✅ Troubleshooting guides

## Dependencies

### Control Node
- Ansible 2.9+
- Python 3.8+
- SSH client
- Bash 4.0+

### Target Hosts
- Ubuntu 22.04 LTS Server
- Python 3.8+
- Sudo access
- Network connectivity

### Optional Tools
- Lynis (for security scanning)
- OpenSSL (for PKI module)

## Maintenance

### Regular Tasks
1. Update Ansible playbooks with latest security recommendations
2. Review and update hardening checklist
3. Test playbooks in non-production
4. Update evidence collection scripts
5. Review and update documentation

### Version Control
- Commit playbooks and scripts
- Do NOT commit evidence files (may contain sensitive data)
- Use `.gitignore` to exclude temporary files

## Extending Phase 1

### Adding New Roles
1. Create role directory in `ansible/roles/`
2. Add tasks, handlers, templates as needed
3. Include role in `ansible/playbooks/harden.yml`
4. Update documentation

### Adding New Validation
1. Add checks to `scripts/post-hardening-validation.sh`
2. Update expected results in README
3. Add evidence collection if needed

### Customizing for Environment
1. Update inventory variables
2. Modify role defaults
3. Add environment-specific tasks
4. Document customizations
