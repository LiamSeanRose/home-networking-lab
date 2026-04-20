# Phase 2 — Network Topology (Containerlab + VXLAN-EVPN)

Spine-leaf data center fabric using Arista cEOS containers, deployed via Containerlab on a Terraform-provisioned Ubuntu host.

## Topology

- **1 spine** (`spine1`) — AS 65000, loopback `10.0.0.1`
- **2 leaves** (`leaf1`, `leaf2`) — AS 65001 / 65002, loopbacks `10.0.0.11` / `10.0.0.12`
- Spine connects to each leaf with a `/31` p2p link
- Underlay: eBGP for IPv4 unicast
- Overlay (in progress): MP-BGP EVPN address family for VXLAN data plane

## Status

- [x] Containerlab deploys 3-node topology cleanly (`evpn-fabric.clab.yml`)
- [x] cEOS 4.36.0F running on all nodes
- [x] Layer 3 underlay (eBGP IPv4 unicast) — full mesh reachability between loopbacks
- [x] EVPN address family activated on all BGP sessions
- [x] VLAN 100 → VNI 10100 mapping configured on both leaves
- [x] IMET (Type-3) routes generated and visible at spine
- [ ] **Pending:** EVPN route propagation between leaves across eBGP spine. cEOS-Lab quirk on cross-AS EVPN reflection. Next session: rewrite overlay as iBGP (single-ASN EVPN domain) per the production reference design.
- [ ] L3 SVI verification ping across overlay
- [ ] Phase 3 — Automation (NAPALM + pyATS)

## Files

- `evpn-fabric.clab.yml` — Containerlab topology definition
- `configs/spine1.cfg`, `configs/leaf1.cfg`, `configs/leaf2.cfg` — captured running configs from each device
- `README.md` — this file

## Deploy / Destroy

From this directory on the lab VM:

```bash
sudo containerlab deploy  -t evpn-fabric.clab.yml   # bring up the fabric
sudo containerlab destroy -t evpn-fabric.clab.yml   # tear it down
sudo containerlab inspect -t evpn-fabric.clab.yml   # status check
```

## Lessons / Notes

- cEOS-Lab is the free Docker-shipped image; some EVPN behaviors (cross-AS reflection in particular) differ from production EOS.
- `Estab(NotNegotiated)` in BGP summary always means "TCP session up but the address family wasn't activated on at least one side." Usually a typo or missed `activate` line.
- `next-hop-self` and `next-hop-unchanged` apply per address family. The same peer group can need both — `next-hop-self` for IPv4 underlay (so leaves know how to reach reflected loopbacks), `next-hop-unchanged` for EVPN (so leaves tunnel VXLAN to the originating leaf, not the spine).
