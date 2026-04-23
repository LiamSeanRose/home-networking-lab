# Phase 3 — Network Automation (NAPALM + pyATS)

Python-based automation scripts and tests that manage the Phase 2 EVPN fabric. Replaces manual SSH-and-eyeball network operations with programmatic configuration, verification, and testing.

## What's here

| File | What it does |
|------|--------------|
| `01_check_bgp.py` | Reads BGP neighbor state from all 3 routers in parallel via NAPALM; prints a unified table. |
| `02_push_vlan.py` | Stages a new VLAN+VNI on both leaves using NAPALM's diff-then-commit pattern; prompts for approval before applying. |
| `testbed.yaml` | pyATS inventory describing the 3 routers (name, OS, IP, credentials-via-env). |
| `test_fabric.py` | 7-case pytest suite: reachability, BGP underlay, BGP overlay, VNI presence, architectural invariants, Type-2 MAC learning after stimulated traffic. |
| `.env.example` | Template for credentials. Copy to `.env`, fill in. Never committed. |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install napalm "pyats[full]" python-dotenv pytest
cp .env.example .env   # then edit .env with real credentials
```

## Daily use

```bash
# activate venv and load credentials
source venv/bin/activate
set -a; source .env; set +a

# check BGP health across the fabric
python 01_check_bgp.py

# push a new VLAN (edit NEW_VLAN/NEW_VNI in the script first)
python 02_push_vlan.py

# run the full test suite
pytest test_fabric.py -v
```

## Design notes

- **Parallel device connections** — both `01_check_bgp.py` and `02_push_vlan.py` use `ThreadPoolExecutor` to query/configure all devices concurrently. Scales cleanly from 3 to 300 devices.
- **Stage-diff-commit pattern** — `02_push_vlan.py` never blindly pushes config. It stages, shows diffs, and requires explicit approval. Same pattern as `terraform plan`/`terraform apply`.
- **pyATS for testing, NAPALM for data** — Genie's Arista EOS parser coverage is incomplete for this cEOS-Lab image. The test suite uses `device.execute()` for raw CLI output combined with lightweight regex helpers. Hybrid approach is common in real NetDevOps work.
- **Credentials via `.env`** — same pattern as Phase 1's `terraform.tfvars`. Secrets out of source code, loaded at runtime.

## Lessons learned

- Genie's parser library has uneven coverage across vendors. Cisco IOS-XE/NX-OS is comprehensive; Arista EOS is patchier. Plan for fallback to raw `execute()` + custom parsing when Genie gaps appear.
- `SchemaEmptyParserError` means a parser exists but didn't match the output — usually a version skew between the parser's expected format and what the device returned.
- Regex-parsing CLI output is fragile. Multi-line entries, continuation indentation, and "extra" rows (e.g. same VNI showing up on multiple ports) all require careful regex design. When in doubt, widen the match and filter in Python.
