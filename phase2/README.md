# Phase 2 — Network Topology (Containerlab + VXLAN-EVPN)

Spine-leaf data center fabric using Arista cEOS containers, deployed via Containerlab on a Terraform-provisioned Ubuntu host. Two Alpine Linux hosts demonstrate end-to-end L2 connectivity across the overlay.

## Topology
┌─────────┐
          │ spine1  │ AS 65000 / local-as 65100
          │ 10.0.0.1│
          └─┬─────┬─┘
            │     │
     ┌──────┘     └──────┐
     │                   │
┌────┴─────┐        ┌────┴─────┐
│  leaf1   │        │  leaf2   │
│10.0.0.11 │        │10.0.0.12 │
│ AS 65001 │        │ AS 65002 │
└────┬─────┘        └────┬─────┘
     │                   │
┌────┴─────┐        ┌────┴─────┐
│  host1   │        │  host2   │
│10.100.100.11       │10.100.100.12
└──────────┘        └──────────┘

## Design

- **Underlay:** eBGP across spine-leaf p2p `/31` links. Per-device ASNs (65000 spine, 65001/65002 leaves). Loopback reachability distributed via IPv4 unicast, `next-hop-self` on spine.
- **Overlay:** MP-BGP EVPN session layered on top, peered loopback-to-loopback. All three devices present themselves as AS 65100 via `local-as ... no-prepend replace-as` — effectively creating an iBGP domain on top of the eBGP underlay. Spine acts as route reflector, leaves are RR clients.
- **Data plane:** VXLAN with VNI 10100 mapped to VLAN 100. Each leaf sources VTEP traffic from its loopback.
- **Demonstrated:** Type-3 IMET routes distribute VTEP membership; Type-2 MAC/IP routes distribute host MAC reachability. Host1 ↔ host2 ping succeeds with Type-2 routes visible in EVPN table and remote MAC installed in the VXLAN forwarding table.

## Files

- `evpn-fabric.clab.yml` — Containerlab topology (3 cEOS + 2 Alpine hosts)
- `configs/spine1.cfg`, `configs/leaf1.cfg`, `configs/leaf2.cfg` — running configs from each device
- `README.md` — this file

## Deploy / Destroy

```bash
sudo containerlab deploy  -t evpn-fabric.clab.yml
sudo containerlab destroy -t evpn-fabric.clab.yml
sudo containerlab inspect -t evpn-fabric.clab.yml
```

## Verification commands

```bash
# From the lab VM: ping across the overlay
docker exec clab-evpn-fabric-host1 ping -c 3 10.100.100.12

# On a leaf: see EVPN routes
ssh admin@172.20.20.21
show bgp evpn summary
show bgp evpn route-type mac-ip
show vxlan address-table
```

## Lessons learned

- **cEOS-Lab does not support cross-AS EVPN route propagation.** Classic eBGP-everywhere fabric design from RFC 7938 doesn't work on this specific image. Solution: `local-as` to fake iBGP for the overlay on top of eBGP underlay. This is a real DC design pattern ("eBGP-over-iBGP" or "overlay ASN") and happens to also sidestep the cEOS-Lab limitation.
- **`Estab(NotNegotiated)` in BGP summary** always means the TCP session is up but the address family wasn't activated on at least one side. 99% of the time it's a missed `activate` or a peer group typo.
- **`next-hop-self` vs `next-hop-unchanged`** are per-address-family settings. Same peer group can need both — `next-hop-self` for IPv4 underlay (so reflected loopbacks become reachable next-hops), iBGP's default `next-hop-unchanged` behavior for EVPN (so leaves tunnel directly to each other's VTEPs, not via spine).
- **Type-2 EVPN advertisement requires host-originated traffic.** SVI-to-SVI traffic doesn't populate the bridge MAC table on cEOS-Lab, so `redistribute learned` has nothing to export. Attaching actual endpoint containers (Alpine hosts) to access ports on the leaves fixes this and is the realistic reference design anyway.
