# Home Networking Lab

A fully virtualized, automated, and security-hardened home networking lab built on a single consumer PC. Designed to spin up and tear down on demand, leaving the daily-use environment untouched.

## Architecture

- **Hypervisor:** Proxmox VE 9.1 (Debian 13 Trixie)
- **Infrastructure as Code:** Terraform with the bpg/proxmox provider
- **VM Provisioning:** Ubuntu 24.04 cloud-init templates (customized with `virt-customize`)
- **Network Topology:** Containerlab running Arista cEOS 4.36 — 1 spine, 2 leaves
- **Upcoming — Automation:** Python + NAPALM + Cisco pyATS for vendor-agnostic config and testing
- **Upcoming — Security:** Zeek + ELK stack for NDR; Tailscale for zero-trust access

## Roadmap

- [x] **Phase 1** — Infrastructure Setup (Proxmox + Terraform)
- [x] **Phase 2** — Network Topology (Containerlab + VXLAN-EVPN) — see [`phase2/README.md`](phase2/README.md)
- [ ] **Phase 3** — Automation (NAPALM + pyATS)
- [ ] **Phase 4** — Security & ZTNA (Zeek + ELK + Tailscale)

## Phase 1 Usage

```powershell
.\start-lab.ps1   # Spin up the Proxmox-hosted lab VM
.\stop-lab.ps1    # Tear it down
```

Configuration lives in `terraform.tfvars` (gitignored — see `terraform.tfvars.example` for the expected format).

## Phase 2 Usage

On the lab VM:

```bash
cd ~/evpn-lab
sudo containerlab deploy  -t evpn-fabric.clab.yml   # bring up the spine-leaf fabric
sudo containerlab destroy -t evpn-fabric.clab.yml   # tear it down
sudo containerlab inspect -t evpn-fabric.clab.yml   # status check
```

Captured device configs live in `phase2/configs/`.

## Project Structure
network-lab/
├── provider.tf           # Proxmox provider + connection config
├── variables.tf          # Input variables with defaults
├── main.tf               # VM resource definitions
├── terraform.tfvars      # Secrets (gitignored)
├── start-lab.ps1         # Convenience: spin up Proxmox VM
├── stop-lab.ps1          # Convenience: tear down Proxmox VM
├── phase2/
│   ├── evpn-fabric.clab.yml
│   ├── configs/          # spine1.cfg, leaf1.cfg, leaf2.cfg
│   └── README.md         # Phase 2 status + lessons
└── .gitignore

## Notes

Built and documented summer 2026 as a NetDevOps learning project.