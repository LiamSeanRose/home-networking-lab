"""
02_push_vlan.py — Push a new VLAN + VNI mapping to both leaves via NAPALM.

Uses the stage-diff-commit pattern:
  1. Load candidate config on each device
  2. Show the diff to the user
  3. Prompt for approval
  4. Commit or discard

Usage:
    python 02_push_vlan.py
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from napalm import get_network_driver

load_dotenv()
USERNAME = os.getenv("NAPALM_USERNAME")
PASSWORD = os.getenv("NAPALM_PASSWORD")

# --- What we're adding ---------------------------------------------------
NEW_VLAN = 200
NEW_VNI = 10200
VLAN_NAME = "Tenant_B"
RT = f"1:{NEW_VNI}"  # route target

# --- Inventory — leaves only; spine doesn't host VLANs ------------------
LEAVES = [
    {"name": "leaf1", "hostname": "172.20.20.21", "loopback": "10.0.0.11", "asn": 65001},
    {"name": "leaf2", "hostname": "172.20.20.22", "loopback": "10.0.0.12", "asn": 65002},
]


def build_config(leaf):
    """Render the config snippet for a specific leaf."""
    return f"""vlan {NEW_VLAN}
   name {VLAN_NAME}
!
interface Vxlan1
   vxlan vlan {NEW_VLAN} vni {NEW_VNI}
!
router bgp {leaf['asn']}
   vlan {NEW_VLAN}
      rd {leaf['loopback']}:{NEW_VNI}
      route-target both {RT}
      redistribute learned
"""


def stage_config(leaf):
    """Connect to a leaf, stage the candidate config, return the diff."""
    driver = get_network_driver("eos")
    device = driver(
        hostname=leaf["hostname"],
        username=USERNAME,
        password=PASSWORD,
        optional_args={"transport": "ssh"},
    )

    try:
        device.open()
        config = build_config(leaf)
        device.load_merge_candidate(config=config)
        diff = device.compare_config()
        return (leaf["name"], device, diff, None)
    except Exception as e:
        try:
            device.close()
        except Exception:
            pass
        return (leaf["name"], None, None, str(e))


def commit_or_discard(name, device, approved):
    """Either commit the staged config or discard it."""
    try:
        if approved:
            device.commit_config()
            return (name, "committed", None)
        else:
            device.discard_config()
            return (name, "discarded", None)
    except Exception as e:
        return (name, "error", str(e))
    finally:
        try:
            device.close()
        except Exception:
            pass


def main():
    if not USERNAME or not PASSWORD:
        print("❌ Missing NAPALM_USERNAME or NAPALM_PASSWORD in .env")
        sys.exit(1)

    print(f"Staging VLAN {NEW_VLAN} / VNI {NEW_VNI} on {len(LEAVES)} leaves...\n")

    # Step 1: stage on all leaves in parallel
    with ThreadPoolExecutor(max_workers=len(LEAVES)) as executor:
        staged = list(executor.map(stage_config, LEAVES))

    # Step 2: show diffs, check for errors
    any_errors = False
    for name, device, diff, error in staged:
        print(f"--- {name} ---")
        if error:
            print(f"  ERROR: {error}")
            any_errors = True
            continue
        if not diff.strip():
            print("  (no changes — already configured)")
        else:
            print(diff)
        print()

    if any_errors:
        print("❌ Errors occurred during staging. Aborting.")
        # Clean up any open connections that did succeed
        for name, device, diff, error in staged:
            if device:
                try:
                    device.discard_config()
                    device.close()
                except Exception:
                    pass
        sys.exit(1)

    # Step 3: prompt for approval
    response = input("Commit these changes on both leaves? [y/N]: ").strip().lower()
    approved = response == "y"

    # Step 4: commit or discard in parallel
    results = []
    with ThreadPoolExecutor(max_workers=len(LEAVES)) as executor:
        futures = [
            executor.submit(commit_or_discard, name, device, approved)
            for name, device, diff, error in staged
            if device is not None
        ]
        for future in futures:
            results.append(future.result())

    print()
    for name, status, error in results:
        if error:
            print(f"{name}: ❌ {status} — {error}")
        elif status == "committed":
            print(f"{name}: ✅ committed")
        else:
            print(f"{name}: ⏸  discarded")


if __name__ == "__main__":
    main()
