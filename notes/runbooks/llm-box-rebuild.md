# Runbook — LLM Lab Box Rebuild

Personal ops doc. Designed to be executed step-by-step, optionally with a paired Claude Code instance running on the box itself (over SSH from your Mac).

**Target hardware**
- Ryzen 9 5900X / 64 GB DDR4 / Gigabyte X570 I AM4 (mini-ITX)
- RTX 3080 Ti (12 GB VRAM)
- Cooler Master NR200 chassis
- Cooler Master V850 SFX Gold PSU
- 6-8 TB NVMe SSD storage

**Target outcome**
A clean Ubuntu 24.04 LTS Server install, hardened with the portfolio's Ansible role, with NVIDIA + CUDA + Docker + Ollama wired up and reachable from your Mac dev environment over Tailscale. End state: `curl http://llm-lab-01:11434/api/tags` from your Mac returns the installed Ollama models.

**How to use this doc**
- Each section is a checkpoint. Verify the checkpoint before moving on.
- Commands are exact. Substitutions are in `<ANGLE_BRACKETS>`.
- Pairing with a remote Claude Code agent: SSH into the box, point it at this file, instruct it to "execute up to checkpoint N". The agent should run the commands, paste output, and stop at the next interactive checkpoint.

---

## 0. Pre-rebuild — from your Mac

- [ ] Back up anything you care about from the current install (home dir, SSH keys, Ollama models worth keeping). Copy to a separate drive or another machine.
- [ ] Decide a hostname. Suggested: `llm-lab-01`.
- [ ] Decide your admin username on the new box. Suggested: short, no special characters. Used below as `<ADMIN_USER>`.
- [ ] Generate (or reuse) an Ed25519 SSH keypair on your Mac:
  ```bash
  ssh-keygen -t ed25519 -C "mac@$(hostname -s)" -f ~/.ssh/llm-lab
  cat ~/.ssh/llm-lab.pub   # you'll paste this into the installer
  ```
- [ ] Download Ubuntu 24.04 LTS Server ISO. Verify the SHA-256 against the canonical.com value.
- [ ] Flash to USB (`dd` or balenaEtcher).
- [ ] Have a wired ethernet cable to the box. Wi-Fi during install is more brittle.

**Checkpoint 0**: USB ready, hostname/user decided, public key on hand, ethernet plugged in.

---

## 1. OS install (interactive — at the keyboard)

Boot the USB. In the Ubuntu Server installer:

1. **Language / keyboard**: defaults.
2. **Network**: confirm DHCP leased an IP on the wired NIC. Note the IP — you'll SSH to it after install.
3. **Proxy**: skip.
4. **Mirror**: default.
5. **Storage**: choose **Custom storage layout**.
   - Create a 1 GB EFI System Partition (FAT32, mountpoint `/boot/efi`).
   - Create a Linux LVM partition consuming the rest of the NVMe.
     - Encrypt the LVM with LUKS — pick a strong passphrase you won't forget.
     - Inside LVM, create a single VG and these LVs:
       - `root` — 200 GB, ext4, mount `/`
       - `home` — 200 GB, ext4, mount `/home`
       - `ollama` — at least 1 TB (more is better), ext4, mount `/var/lib/ollama` (you'll make this dir later, the installer just sets the mountpoint)
     - Leave the remaining VG capacity unallocated. You can grow `ollama` later.
6. **Profile setup**:
   - Server name: `llm-lab-01` (or your choice).
   - Username: `<ADMIN_USER>`.
   - Password: long; you'll mostly use SSH keys but you need it for sudo.
7. **SSH setup**: enable OpenSSH server. **Import SSH identity**: pick "No" and paste your `~/.ssh/llm-lab.pub` content into `authorized_keys` after the install instead — easier to control the key precisely.
8. **Featured server snaps**: select nothing.
9. Wait for install. Reboot. Remove USB.

**Checkpoint 1**: box boots from disk, prompts for the LUKS passphrase, presents a login prompt. You can log in locally with your password.

---

## 2. First SSH from your Mac

On the **box** (locally), find its IP:
```bash
ip -br a | grep -v ' lo '
```

On your **Mac**, copy the public key into authorized_keys:
```bash
ssh-copy-id -i ~/.ssh/llm-lab.pub <ADMIN_USER>@<BOX_IP>
ssh -i ~/.ssh/llm-lab <ADMIN_USER>@<BOX_IP>   # password-less now
```

If `ssh-copy-id` is unavailable on macOS:
```bash
cat ~/.ssh/llm-lab.pub | ssh <ADMIN_USER>@<BOX_IP> 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Add an entry to `~/.ssh/config` on your Mac:
```
Host llm-lab
    HostName <BOX_IP>
    User <ADMIN_USER>
    IdentityFile ~/.ssh/llm-lab
    IdentitiesOnly yes
```

Now `ssh llm-lab` works.

**Checkpoint 2**: `ssh llm-lab` succeeds password-less. Everything below runs on the box (over SSH).

---

## 3. Base updates and essentials

```bash
sudo apt update && sudo apt -y full-upgrade
sudo apt install -y \
    build-essential git curl wget jq htop tmux \
    python3-pip python3-venv \
    ca-certificates gnupg lsb-release \
    unattended-upgrades

sudo systemctl reboot
```

After reboot, `ssh llm-lab` again.

**Checkpoint 3**: `apt list --upgradable` is empty.

---

## 4. Apply the linux-hardening-role

This eats the portfolio's own dog food and produces real Lynis evidence you can commit.

On your **Mac** (or wherever Ansible runs — could also be on the box itself):

```bash
cd /Volumes/Complex/Apps/GitHub/security-engineering-portfolio/foundations/linux-hardening-role
```

Edit `ansible/inventory/hosts.yml`: set `ansible_host` to the box's IP (or `llm-lab` if you've added the SSH config), `ansible_user` to `<ADMIN_USER>`, `ansible_ssh_private_key_file` to `~/.ssh/llm-lab`.

Test connectivity:
```bash
ansible all -i ansible/inventory/hosts.yml -m ping
```

Capture baseline (on the box):
```bash
ssh llm-lab 'sudo apt install -y lynis && sudo lynis audit system --quiet' | tee evidence/baseline/lynis-baseline.txt
```

Apply hardening:
```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/harden.yml --check  # dry-run
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/harden.yml          # apply
```

Re-baseline:
```bash
ssh llm-lab 'sudo lynis audit system --quiet' | tee evidence/post/lynis-post.txt
./scripts/compare-lynis.sh evidence/baseline/lynis-baseline.txt evidence/post/lynis-post.txt
```

Verify SSH still works (in a **second terminal** before closing the first):
```bash
ssh llm-lab 'echo ok'
```

**Checkpoint 4**: Lynis hardening index improved by ≥10 points. SSH still works. Evidence saved under `evidence/baseline/` and `evidence/post/`. fail2ban running, UFW active with port 22 only.

---

## 5. NVIDIA driver + CUDA

Confirm hardware is detected:
```bash
lspci | grep -i nvidia
```

Install the recommended driver:
```bash
sudo ubuntu-drivers list
sudo ubuntu-drivers autoinstall
sudo reboot
```

After reboot, verify:
```bash
nvidia-smi
```

Expected: a table showing the RTX 3080 Ti, driver version 550+, 12 GB total memory.

Install CUDA toolkit (matches the driver):
```bash
sudo apt install -y nvidia-cuda-toolkit
nvcc --version
```

**Checkpoint 5**: `nvidia-smi` shows the GPU. `nvcc --version` reports CUDA 12.x.

---

## 6. Docker + NVIDIA Container Toolkit

```bash
# Docker CE
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in

# Verify
docker run --rm hello-world

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access from container
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

**Checkpoint 6**: `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi` prints the same table as the host.

---

## 7. Ollama

Install:
```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl status ollama
```

Override the systemd unit so Ollama binds to `0.0.0.0` (Tailscale will firewall it):
```bash
sudo systemctl edit ollama
```

Add:
```
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/var/lib/ollama"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Pull a starter model and verify GPU usage:
```bash
ollama pull qwen2.5:14b-instruct-q4_K_M     # ~9 GB, fits 12 GB VRAM
ollama run qwen2.5:14b-instruct-q4_K_M "Say 'hello' and exit."
nvidia-smi   # in another shell while the model is loaded — should show ~9 GB used
```

**Checkpoint 7**: model responds. `nvidia-smi` shows VRAM occupied while inference is running.

---

## 8. Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=llm-lab-01
```

Authenticate via the URL it prints. On your **Mac**, install Tailscale (if not already), join the same tailnet.

UFW: tighten so only Tailscale (and LAN SSH) reach Ollama:
```bash
sudo ufw allow in on tailscale0 to any port 11434 proto tcp comment 'ollama via tailscale'
sudo ufw status verbose
```

Confirm there is no `11434` allow rule on the LAN interface. If `harden.yml` already restricts UFW correctly this is a no-op.

From your **Mac**:
```bash
curl http://llm-lab-01:11434/api/tags
```

Expected: a JSON list including `qwen2.5:14b-instruct-q4_K_M`.

**Checkpoint 8**: Mac can reach Ollama API over Tailscale by hostname. LAN cannot.

---

## 9. Wire the portfolio repo to local Ollama

On your **Mac**:
```bash
echo 'export OLLAMA_HOST=http://llm-lab-01:11434' >> ~/.zshrc   # or ~/.bashrc
echo 'export LLM_BACKEND=ollama' >> ~/.zshrc
source ~/.zshrc
```

When you start working on the alert-triage agent, those two env vars are all that's needed to route inference to the box. Anthropic remains available as the eval-class backend by setting `LLM_BACKEND=anthropic` and `ANTHROPIC_API_KEY=...`.

**Checkpoint 9**: a `make run` against an LLM-using project picks up the local backend without further config.

---

## 10. Model selection bench (optional, do later)

Once the alert-triage agent exists, run its eval harness against multiple local models to pick your daily driver:

```bash
for m in qwen2.5:14b-instruct-q4_K_M phi4:14b-q4_K_M deepseek-r1:14b-q4_K_M llama3.1:8b-instruct-q4_K_M; do
    ollama pull $m
    LLM_BACKEND=ollama OLLAMA_MODEL=$m make eval
done
```

Compare accuracy / FP rate / schema-validation rate / latency. Commit the comparison table as evidence under the alert-triage project.

---

## Operational reference

| Task | Command |
|---|---|
| List installed models | `ollama list` |
| Remove a model | `ollama rm <name>` |
| Watch GPU live | `watch -n 0.5 nvidia-smi` |
| Tailscale status | `tailscale status` |
| Lynis re-scan | `sudo lynis audit system --quiet` |
| Apt unattended log | `journalctl -u unattended-upgrades` |
| Update everything | `sudo apt update && sudo apt -y full-upgrade && sudo systemctl reboot` |

## If something breaks

- **Locked out of SSH**: console into the box, restore `/etc/ssh/sshd_config.bak`, restart sshd.
- **NVIDIA driver mismatch after kernel update**: `sudo apt install --reinstall nvidia-driver-<VERSION>` then reboot.
- **Ollama eats VRAM, GPU OOM**: smaller model, lower context (`--ctx-size 8192`), or quantize harder (Q3_K_M instead of Q4_K_M).
- **Tailscale can't connect**: `sudo tailscale down && sudo tailscale up --ssh --hostname=llm-lab-01`.
- **Hardening role broke a service**: `ansible-playbook ansible/playbooks/rollback.yml` from the role directory.

## Next

Once Checkpoint 9 is green, the box is done. The alert-triage agent will use it as the default `LLM_BACKEND=ollama` endpoint; the eval harness uses Anthropic. Hybrid as designed.
