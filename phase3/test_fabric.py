"""
test_fabric.py — Network health tests for the EVPN fabric.

Run with:
    pytest test_fabric.py -v

Each test asserts a specific property of the network. All tests run against
a live fabric described in testbed.yaml.
"""

import os
import re
import pytest
from dotenv import load_dotenv
from genie.testbed import load

# Load credentials into env before loading the testbed
load_dotenv()


# --- Fixtures -------------------------------------------------------------
# A fixture in pytest is a reusable setup/teardown helper.
# This one connects to all devices once, yields them to tests, disconnects.

@pytest.fixture(scope="session")
def fabric():
    """Connect to all devices, yield the testbed, disconnect on teardown."""
    tb = load("testbed.yaml")
    for name, device in tb.devices.items():
        device.connect(log_stdout=False, learn_hostname=True)
    yield tb
    for device in tb.devices.values():
        try:
            device.disconnect()
        except Exception:
            pass


# --- Helper functions -----------------------------------------------------

def count_established_bgp(device, cmd="show ip bgp summary"):
    """Count BGP neighbors in Established state from raw CLI output."""
    output = device.execute(cmd)
    # Each data row has a peer IP, then columns; 'Estab' in the state column
    return sum(1 for line in output.splitlines() if "Estab" in line)


def get_vxlan_vnis(device):
    """Parse `show vxlan vni` to extract configured VNIs.

    Match any line that starts with a number between 4096 and 16777214
    (the valid VXLAN VNI range per RFC 7348). Continuation lines (which
    start with whitespace) are naturally skipped.
    """
    output = device.execute("show vxlan vni")
    vnis = []
    for line in output.splitlines():
        m = re.match(r"^(\d+)\s", line)
        if m:
            vni = int(m.group(1))
            # VNIs are 24-bit; values under 4096 would be a VLAN ID or
            # table-formatting dashes misread as numbers. Gate conservatively.
            if 4096 <= vni <= 16777214:
                vnis.append(vni)
    return sorted(set(vnis))  # dedupe in case same VNI printed twice

def count_evpn_mac_ip_routes(device):
    """Count EVPN Type-2 (MAC/IP) routes."""
    output = device.execute("show bgp evpn route-type mac-ip")
    # Each route row contains " mac-ip " with a MAC address after
    return sum(1 for line in output.splitlines() if "mac-ip" in line)


# --- Test cases -----------------------------------------------------------

def test_all_devices_reachable(fabric):
    """Every device in the testbed should be connected."""
    for name, device in fabric.devices.items():
        assert device.connected, f"{name} failed to connect"


def test_underlay_bgp_sessions_established(fabric):
    """Every device should have all its IPv4-unicast BGP sessions Established."""
    expected = {"spine1": 2, "leaf1": 1, "leaf2": 1}
    for name, count in expected.items():
        device = fabric.devices[name]
        actual = count_established_bgp(device, "show ip bgp summary")
        assert actual >= count, (
            f"{name} expected >={count} Established sessions, got {actual}"
        )


def test_evpn_bgp_sessions_established(fabric):
    """Every device should have all its EVPN BGP sessions Established."""
    expected = {"spine1": 2, "leaf1": 1, "leaf2": 1}
    for name, count in expected.items():
        device = fabric.devices[name]
        actual = count_established_bgp(device, "show bgp evpn summary")
        assert actual >= count, (
            f"{name} expected >={count} EVPN sessions, got {actual}"
        )


def test_vxlan_vni_10100_on_both_leaves(fabric):
    """VNI 10100 (Tenant_A) should be configured on leaf1 and leaf2."""
    for name in ["leaf1", "leaf2"]:
        device = fabric.devices[name]
        vnis = get_vxlan_vnis(device)
        assert 10100 in vnis, f"{name} missing VNI 10100, has {vnis}"


def test_vxlan_vni_10200_on_both_leaves(fabric):
    """VNI 10200 (Tenant_B) should be configured — this tests the VLAN we pushed earlier."""
    for name in ["leaf1", "leaf2"]:
        device = fabric.devices[name]
        vnis = get_vxlan_vnis(device)
        assert 10200 in vnis, f"{name} missing VNI 10200, has {vnis}"


def test_spine_has_no_vxlan(fabric):
    """Spine should NOT have VXLAN VNIs — it only routes, never encapsulates."""
    spine = fabric.devices["spine1"]
    vnis = get_vxlan_vnis(spine)
    assert vnis == [], f"spine1 should have no VNIs, has {vnis}"


def test_type2_routes_present_after_ping(fabric):
    """After host-to-host traffic, each leaf should have MAC-IP routes in EVPN."""
    # First, trigger Type-2 learning by pinging host-to-host.
    # We use a raw docker exec from within the test, which works because
    # pytest runs on the lab VM where docker is available.
    os.system(
        "docker exec clab-evpn-fabric-host1 ping -c 3 -W 1 10.100.100.12 > /dev/null 2>&1"
    )
    # Now verify leaves see MAC-IP routes
    for name in ["leaf1", "leaf2"]:
        device = fabric.devices[name]
        count = count_evpn_mac_ip_routes(device)
        assert count >= 1, f"{name} has no EVPN MAC-IP routes"
