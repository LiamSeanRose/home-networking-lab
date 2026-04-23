"""
01_check_bgp.py — Read BGP neighbor state across the whole fabric via NAPALM.

Usage:
    python 01_check_bgp.py
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from napalm import get_network_driver

# Load credentials from .env into environment variables
load_dotenv()
USERNAME = os.getenv("NAPALM_USERNAME")
PASSWORD = os.getenv("NAPALM_PASSWORD")

# Fabric inventory — hostname and management IP for each router
# In a bigger project this would live in a YAML file, not hardcoded.
DEVICES = [
    {"name": "spine1", "hostname": "172.20.20.11"},
    {"name": "leaf1",  "hostname": "172.20.20.21"},
    {"name": "leaf2",  "hostname": "172.20.20.22"},
]


def fetch_bgp(device_info):
    """Connect to a single device, fetch BGP neighbors, return results."""
    name = device_info["name"]
    hostname = device_info["hostname"]

    # Get the Arista EOS driver class from NAPALM
    driver = get_network_driver("eos")

    # Instantiate a device object — this does NOT connect yet
    device = driver(
        hostname=hostname,
        username=USERNAME,
        password=PASSWORD,
        optional_args={"transport": "ssh"},
    )

    try:
        device.open()  # establishes SSH session
        bgp = device.get_bgp_neighbors()
        return (name, bgp, None)  # success: (name, data, no-error)
    except Exception as e:
        return (name, None, str(e))  # failure: (name, no-data, error msg)
    finally:
        try:
            device.close()
        except Exception:
            pass  # ignore close errors


def print_bgp_table(results):
    """Render collected BGP data as an aligned table."""
    print()
    header = f"{'Device':<10} {'Neighbor':<16} {'Remote AS':<10} {'State':<6} {'Uptime(s)':<10} {'Rx Pfx':<8}"
    print(header)
    print("-" * len(header))

    for name, bgp_data, error in results:
        if error:
            print(f"{name:<10} ERROR: {error}")
            continue

        # bgp_data is nested under "global" for the default VRF
        peers = bgp_data.get("global", {}).get("peers", {})

        if not peers:
            print(f"{name:<10} (no BGP peers)")
            continue

        for peer_ip, peer_info in peers.items():
            remote_as = peer_info.get("remote_as", "?")
            is_up = peer_info.get("is_up", False)
            state = "Up" if is_up else "Down"
            uptime = peer_info.get("uptime", 0)

            # address_family is nested: {family_name: {received_prefixes, ...}}
            rx_pfx = 0
            for af_data in peer_info.get("address_family", {}).values():
                rx_pfx += af_data.get("received_prefixes", 0)

            print(f"{name:<10} {peer_ip:<16} {remote_as:<10} {state:<6} {uptime:<10} {rx_pfx:<8}")
    print()


def main():
    if not USERNAME or not PASSWORD:
        print("❌ Missing NAPALM_USERNAME or NAPALM_PASSWORD in .env")
        return

    print(f"Querying {len(DEVICES)} devices in parallel...")

    results = []
    # ThreadPoolExecutor runs fetch_bgp() for each device concurrently
    with ThreadPoolExecutor(max_workers=len(DEVICES)) as executor:
        # Submit all tasks
        future_to_device = {
            executor.submit(fetch_bgp, d): d["name"] for d in DEVICES
        }
        # Collect results as they complete (order not guaranteed)
        for future in as_completed(future_to_device):
            results.append(future.result())

    # Sort by device name for consistent output
    results.sort(key=lambda r: r[0])

    print_bgp_table(results)


if __name__ == "__main__":
    main()
