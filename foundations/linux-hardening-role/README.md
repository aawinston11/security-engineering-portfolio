# Linux Hardening Role

Idempotent Ansible role that brings an Ubuntu 22.04 host to a CIS/NIST-aligned baseline: SSH, UFW, PAM, auditd, fail2ban, kernel parameters. Lynis baseline/post evidence; safe rollback.

**Status: Beta.** Code is functional and idempotent; full Lynis evidence run pending against a clean target VM.

---

## Problem

A senior portfolio without baseline hardening is incomplete; baseline hardening as a 16-phase saga is overdone. This is the small, opinionated version: one OS, one role, evidence in, evidence out, runs in a couple of minutes.

## What I built

- Ansible roles: `system_updates`, `ssh_hardening`, `firewall`, `pam_config`, `auditd_config`, `fail2ban_config`, `system_hardening`. Each is idempotent and tagged.
- A `harden.yml` orchestrator and a `rollback.yml` companion that restores from on-disk backups taken at run time.
- Validation scripts: `baseline-assessment.sh`, `post-hardening-validation.sh`, `compare-lynis.sh`.
- Evidence layout: `evidence/baseline/` and `evidence/post/` for Lynis output, `sshd -T`, `ufw status`, `fail2ban-client status`, `auditctl -l`.

## How it works

| Domain | Control | Evidence |
|---|---|---|
| Access control | SSH key-only, root login disabled, PAM policy | `evidence/post/ssh_config`, `pam_config` |
| Network | UFW default-deny + allowlist, rate-limited SSH | `evidence/post/ufw_status` |
| Integrity | auditd rules: auth, file changes, privilege escalation | `evidence/post/auditd_rules` |
| Intrusion prevention | fail2ban SSH jail | `evidence/post/fail2ban_status` |
| Patch | unattended-upgrades on the security pocket | `evidence/post/apt_upgrade` |
| Kernel | sysctl hardening (rp_filter, syncookies, ICMP, IPv6 RA) | `evidence/post/sysctl` |

Threat model summary (full STRIDE in `docs/hardening-checklist.md`): the role addresses spoofing (key-only auth + fail2ban), tampering (auditd), repudiation (auditd), and elevation of privilege (PAM + sudo restrictions). Information disclosure and denial-of-service are partially addressed and explicitly out of scope at this baseline.

## Run it

```bash
# 1. Edit the inventory: set ansible_host, ansible_user, ssh key path.
$EDITOR ansible/inventory/hosts.yml

# 2. Test connectivity.
ansible all -i ansible/inventory/hosts.yml -m ping

# 3. Baseline.
./scripts/baseline-assessment.sh <inventory-host>
ssh <inventory-host> 'sudo lynis audit system' | tee evidence/baseline/lynis-baseline.txt

# 4. Harden.
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/harden.yml

# 5. Validate.
./scripts/post-hardening-validation.sh <inventory-host>
ssh <inventory-host> 'sudo lynis audit system' | tee evidence/post/lynis-post.txt
./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt
```

Prerequisites: Ansible 2.14+, an Ubuntu 22.04 LTS target with sudo and key-based SSH.

## Interview-ready

- **Risk reduced:** SSH password brute-force surface eliminated; ingress reduced to allowlist; brute-force attempts blocked automatically; auth events logged for forensic review.
- **Failure modes:** SSH lockout if the operator hasn't pre-staged a key (mitigation: console access via the hypervisor, `rollback.yml`); UFW default-deny can block legitimate services if `allowed_ports` isn't customized for the workload; auditd is verbose and can fill `/var/log` — log rotation and remote shipping are out of scope here.
- **Detection / monitoring:** fail2ban journal; auditd events for `EXECVE`, `USER_AUTH`, file PATH watches; Lynis hardening index trend over time; `unattended-upgrades` exit logs.
- **Rollback:** `rollback.yml` restores `sshd_config`, UFW, fail2ban, and auditd from backups taken in `harden.yml`. Manual fallback documented in `docs/implementation.md`.
- **Scale:** Ansible handles host count fine. The real scale problems are evidence collection, log shipping, and configuration drift — none of which this role solves; that's the job of the SIEM and a config-management control plane (out of scope).

## Layout

```
foundations/linux-hardening-role/
├── ansible/
│   ├── inventory/hosts.yml          # example, edit before use
│   ├── playbooks/{harden,rollback}.yml
│   └── roles/{system_updates,ssh_hardening,firewall,pam_config,auditd_config,fail2ban_config,system_hardening}/
├── scripts/{baseline-assessment,post-hardening-validation,compare-lynis}.sh
├── docs/{hardening-checklist,implementation}.md
└── evidence/{baseline,post}/
```

## References

- CIS Ubuntu 22.04 LTS Benchmark — https://www.cisecurity.org/benchmark/ubuntu_linux
- NIST SP 800-53 Rev. 5 — controls AC-17, AU-2/3, IA-5, SC-7, SI-2/4/7
- Lynis — https://cisofy.com/lynis/
- MITRE ATT&CK techniques addressed (representative): T1110 (Brute Force), T1078 (Valid Accounts), T1059 (Command and Scripting Interpreter), T1543 (Create or Modify System Process)
