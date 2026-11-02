# Home Networking Lab

This is a NetDevOps lab I built on one regular PC. I use Terraform to build the lab VM on Proxmox. Inside that VM, Containerlab runs a VXLAN-EVPN spine-leaf fabric on Arista cEOS. I configure and test the fabric with Python (NAPALM and pyATS), and Zeek and ELK watch the traffic. I connect to it remotely through Tailscale, so no ports are open. I can tear the whole thing down and rebuild it from this repo.

## Why I built this

At the start of the summer I was doing alright in school, but I felt like what I actually knew was pretty limited. I knew I could do better if I really tried to learn, so I picked a project that wouldn't be taught in class: tools that make a real difference at work and that not many people my age have used. AI can already do a lot in networking, so I wanted to learn the newer technologies and skills that will still matter. I also wanted to do it as cheaply as possible, which is why it all runs on one PC.

This lab was my first step. Every project I've done since has been another step up from it.

## Build guide

If you want to build it yourself, the full guide is in [`docs/LAB-GUIDE.md`](docs/LAB-GUIDE.md). Each phase folder also has its own README.

## Stack

| Layer | Tool | Version used |
|---|---|---|
| Hypervisor | Proxmox VE | 9.1.7 (Debian 13 Trixie) |
| VM provisioning | Terraform + `bpg/proxmox` provider | Terraform 1.5+, provider 0.60+ |
| Lab VM | Ubuntu cloud image with cloud-init | 24.04 LTS |
| Fabric | Containerlab + Arista cEOS-lab | Containerlab 0.74, cEOS 4.36.0F |
| Automation | Python, NAPALM, pyATS/Genie, pytest | Python 3.12, NAPALM 5.1, pyATS 26.3 |
| Sensor | Zeek | 8.x |
| Logs | Filebeat, Elasticsearch, Kibana | 8.x, 8.15.0, 8.15.0 |
| Remote access | Tailscale | free personal plan |

## Phases

- [x] Phase 1: Infrastructure. Proxmox host, Ubuntu cloud-init template, Terraform VM pipeline. Files are in the repo root.
- [x] Phase 2: Network topology. 1 spine, 2 leaves, eBGP underlay, iBGP EVPN overlay, VXLAN VNI 10100. See [`phase2/`](phase2/README.md).
- [x] Phase 3: Automation. NAPALM BGP check, NAPALM VLAN push with diff and approval, 7-test pyATS suite. See [`phase3/`](phase3/README.md).
- [x] Phase 4: Security and observability. Zeek, Filebeat, Elasticsearch, Kibana dashboard, Tailscale. See [`phase4/`](phase4/README.md).

## Quick start

These commands only work if Phase 1 is already done (Proxmox host, template 9000, `terraform.tfvars`). The guide walks through that part.

From the Windows workstation:

```powershell
.\start-lab.ps1   # terraform apply, prints the VM IP
.\stop-lab.ps1    # terraform destroy
```

On the lab VM:

```bash
# Phase 2: fabric
cd phase2
sudo containerlab deploy -t evpn-fabric.clab.yml
docker exec clab-evpn-fabric-host1 ping -c 3 10.100.100.12

# Phase 3: automation and tests
cd ../phase3
python3 -m venv venv && source venv/bin/activate
pip install napalm "pyats[full]" python-dotenv pytest
cp .env.example .env            # cEOS default login is admin / admin
python 01_check_bgp.py
python 02_push_vlan.py          # adds VLAN 200 / VNI 10200
pytest test_fabric.py -v        # 7 passed

# Phase 4: observability (Zeek + Filebeat installed on the host, see guide)
cd ../phase4
docker compose up -d            # Elasticsearch + Kibana on :5601
```

## Repo layout

```
home-networking-lab/
├── provider.tf, variables.tf, main.tf   Phase 1: Terraform for the lab VM
├── terraform.tfvars.example             token format (real tfvars is gitignored)
├── start-lab.ps1, stop-lab.ps1          apply / destroy wrappers
├── phase2/
│   ├── evpn-fabric.clab.yml             Containerlab topology
│   ├── configs/                         startup configs for spine1, leaf1, leaf2
│   └── containerlab-evpn.service        systemd unit that redeploys the fabric on boot
├── phase3/
│   ├── 01_check_bgp.py                  BGP table across the fabric (NAPALM)
│   ├── 02_push_vlan.py                  stage, diff, approve, commit (NAPALM)
│   ├── testbed.yaml                     pyATS inventory
│   └── test_fabric.py                   pytest suite
├── phase4/
│   ├── docker-compose.yml               Elasticsearch + Kibana
│   ├── filebeat.yml                     Zeek module config for Filebeat
│   └── phase4-dashboard.png
└── docs/
    └── LAB-GUIDE.md                     full build guide, all four phases
```

## Hardware

My host PC has 32 GB of RAM, an RTX 3070, and its own NVMe drive for Proxmox. I give the lab VM 12 GB and 6 vCPU, which is enough to run all four phases at once. If you only need Phases 2 and 3, 8 GB is enough.

## License

MIT. See [LICENSE](LICENSE).

Built by Liam Rose, April 2026.
