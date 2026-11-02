# Phase 3: Network automation (NAPALM + pyATS)

Once the fabric worked, I wanted to stop configuring and checking it by hand. So I wrote Python scripts and a test suite for it. NAPALM reads state and pushes config. pyATS connects to the devices and pytest checks that the fabric is healthy. I run all of it on the lab VM, because that's where the cEOS management IPs are reachable.

## Files

| File | What it does |
|---|---|
| `01_check_bgp.py` | Connects to all 3 routers in parallel with NAPALM and prints one BGP table: neighbor, remote AS, state, uptime, received prefixes. |
| `02_push_vlan.py` | Adds VLAN 200 (`Tenant_B`) mapped to VNI 10200 on both leaves. Stages the change, prints the diff from each leaf, asks for approval, then commits or discards. |
| `testbed.yaml` | pyATS inventory for spine1, leaf1, leaf2. Credentials come from environment variables. |
| `test_fabric.py` | 7 pytest cases, listed below. |
| `.env.example` | Template for `.env` (gitignored). |

## Setup

Ubuntu 24.04 blocks `pip install` outside a virtual environment (PEP 668), so use a venv.

```bash
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install napalm "pyats[full]" python-dotenv pytest
cp .env.example .env     # set NAPALM_USERNAME=admin, NAPALM_PASSWORD=admin for the default cEOS login
```

`pyats[full]` pulls in Genie, Unicon and about 50 other packages, so the install takes a few minutes. Versions I ran with: Python 3.12.3, napalm 5.1.0, pyats and genie 26.3, pytest 9.0.3, python-dotenv 1.2.2.

## Use

```bash
source venv/bin/activate
set -a; source .env; set +a

python 01_check_bgp.py      # 8 rows: 4 peers on spine1, 2 on each leaf
python 02_push_vlan.py      # review the diff, answer y to commit
pytest test_fabric.py -v
```

## Tests

| Test | Checks |
|---|---|
| `test_all_devices_reachable` | pyATS connected to all 3 routers |
| `test_underlay_bgp_sessions_established` | IPv4 sessions Established: spine1 2, each leaf 1 |
| `test_evpn_bgp_sessions_established` | EVPN sessions Established: spine1 2, each leaf 1 |
| `test_vxlan_vni_10100_on_both_leaves` | VNI 10100 configured on leaf1 and leaf2 |
| `test_vxlan_vni_10200_on_both_leaves` | VNI 10200 configured, i.e. the push from `02_push_vlan.py` landed |
| `test_spine_has_no_vxlan` | spine1 has no VNIs (it only routes) |
| `test_type2_routes_present_after_ping` | pings host1 to host2, then checks both leaves have EVPN mac-ip routes |

Run order matters. The VNI 10200 test only passes after `02_push_vlan.py` has been committed, so a fresh deploy gives 6 passed and 1 failed until you run the push. The VLAN 200 change is not in the saved startup configs, so it is gone after a redeploy.

The BGP tests count a session only when the state is `Estab`. `Estab(NotNegotiated)` doesn't count, because in that state the session is up but no routes are exchanged.

## Design notes

- Both scripts use `ThreadPoolExecutor` so every device is handled at the same time. Going from 3 devices to 30 doesn't change the run time much.
- `02_push_vlan.py` never pushes blindly. It loads a merge candidate, shows `compare_config()` for each leaf, and only commits after a `y`. Any staging error discards the candidates on all leaves and exits. It is the same idea as `terraform plan` then `terraform apply`.
- Genie's parsers didn't cover the outputs I needed on this cEOS-lab build, so the tests use `device.execute()` for raw CLI text and parse it with small helpers. NAPALM's `get_bgp_neighbors()` returns structured data, so the BGP script didn't need any parsing.
- Credentials live in `.env`, which is gitignored, the same way `terraform.tfvars` is in Phase 1.

## Lessons learned

- Genie parser coverage is uneven between vendors. Cisco IOS-XE and NX-OS are well covered, Arista EOS less so. Plan on falling back to `execute()` plus your own parsing.
- `SchemaEmptyParserError` doesn't mean the parser is missing. It means a parser ran and didn't match the output, usually because the CLI format changed between versions.
- My first regex for `show vxlan vni` only handled single-line entries and missed VNIs that wrap onto continuation lines. Matching any line that starts with a number, then keeping only values in the valid VNI range (4096 to 16777214), was more reliable than trying to match the whole row.
- My first version of the BGP test matched on the string "Estab", which also matches `Estab(NotNegotiated)`. That would have passed on exactly the broken state from Phase 2, so the helper now excludes it.
- Don't `scp -r` a Python project folder. The venv is thousands of files. Copy individual files or exclude `venv/`.
