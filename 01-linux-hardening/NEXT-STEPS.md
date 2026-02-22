# Phase 1 — Where We Left Off & What's Next

## Where We Left Off

**Done:**
- ✅ Phase 1 repo structure (design, ansible, scripts, pki, evidence, docs)
- ✅ Design doc (architecture, VM layout, assumptions, success criteria)
- ✅ CIS/NIST hardening checklist
- ✅ Ansible playbooks and roles (idempotent, with rollback)
- ✅ Validation scripts (baseline, post-hardening, Lynis compare)
- ✅ PKI mini-module (trust store, TLS validation)
- ✅ Enterprise-style README and implementation guide
- ✅ **VM built** (Ubuntu 22.04 LTS on Proxmox)

**Not done yet:**
- ❌ Ansible inventory pointed at your real VM
- ❌ SSH key on VM (password-less Ansible access)
- ❌ Baseline assessment run
- ❌ Hardening playbook run
- ❌ Post-hardening validation and evidence
- ❌ Lynis baseline + post scans and comparison

So we're at: **VM ready → next is wire up inventory, baseline, then harden.**

---

## What's Next (In Order)

### 1. Point inventory at your VM

Edit the Ansible inventory with your VM’s real IP/hostname and user:

```bash
cd 01-linux-hardening/ansible
# Edit inventory/hosts.yml
```

Set at least one host, e.g.:

```yaml
linux_servers:
  hosts:
    ubuntu-server-01:
      ansible_host: <YOUR_VM_IP>   # e.g. 192.168.1.10
      ansible_user: ubuntu          # or your sudo user
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519  # or id_rsa
```

Remove or comment out the second host if you only have one VM.

### 2. Ensure SSH key access to the VM

From your Mac/laptop (control node):

```bash
# If you don’t have a key yet
ssh-keygen -t ed25519 -C "ansible-phase1"

# Copy key to VM (use VM IP and user from inventory)
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@<YOUR_VM_IP>
# Test
ssh -i ~/.ssh/id_ed25519 ubuntu@<YOUR_VM_IP>
```

Ansible must be able to log in without a password.

### 3. Test Ansible connectivity

```bash
cd 01-linux-hardening/ansible
ansible all -i inventory/hosts.yml -m ping
```

You want `SUCCESS` and `"ping": "pong"` for your host(s).

### 4. Run baseline assessment

From repo root:

```bash
cd 01-linux-hardening
./scripts/baseline-assessment.sh ubuntu@<YOUR_VM_IP>
# Or use the inventory host: ./scripts/baseline-assessment.sh ubuntu-server-01
```

Then on the VM (or from control node with Lynis on VM), capture Lynis baseline:

```bash
# On the VM (SSH in first)
sudo apt install -y lynis
sudo lynis audit system --profile /usr/share/lynis/default.prf 2>&1 | tee evidence/baseline/lynis-baseline.txt
```

If you run Lynis from your laptop, you’d need to run it against the VM (e.g. copy script to VM or run Lynis on VM and copy output back). Easiest is run Lynis on the VM and save to `evidence/baseline/lynis-baseline.txt`.

### 5. Run hardening playbook

```bash
cd 01-linux-hardening/ansible
# Optional: dry run first
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --check

# Apply hardening
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml
```

After this, SSH should still work **only with your key** (password auth disabled).

### 6. Run post-hardening validation

```bash
cd 01-linux-hardening
./scripts/post-hardening-validation.sh ubuntu@<YOUR_VM_IP>
```

Capture Lynis again on the VM:

```bash
sudo lynis audit system --profile /usr/share/lynis/default.prf 2>&1 | tee evidence/post/lynis-post.txt
```

### 7. Compare Lynis and collect evidence

```bash
./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt
```

Review `evidence/baseline/` and `evidence/post/`, then update README “Status” and add a short “Lessons learned” if you want.

---

## Quick reference

| Step | Command / Action |
|------|-------------------|
| 1 | Edit `ansible/inventory/hosts.yml` with VM IP and user |
| 2 | `ssh-copy-id` to VM, then `ssh` test |
| 3 | `ansible all -i inventory/hosts.yml -m ping` |
| 4 | `./scripts/baseline-assessment.sh <host>` + Lynis baseline on VM → `evidence/baseline/` |
| 5 | `ansible-playbook -i inventory/hosts.yml playbooks/harden.yml` |
| 6 | `./scripts/post-hardening-validation.sh <host>` + Lynis post on VM → `evidence/post/` |
| 7 | `./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt` |

---

## If something breaks

- **SSH lockout:** Use Proxmox console, restore: `sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config` then `sudo systemctl restart sshd`.
- **Rollback everything:** `ansible-playbook -i inventory/hosts.yml playbooks/rollback.yml` (see README for manual rollback).

Once 1–7 are done, Phase 1 is effectively complete for that VM; you can add more hosts to inventory and re-run the same flow.
