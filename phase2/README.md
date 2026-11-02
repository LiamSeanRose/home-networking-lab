# Phase 2: Network topology (Containerlab + VXLAN-EVPN)

In this phase I built a spine-leaf fabric out of Arista cEOS containers and deployed it with Containerlab on the Ubuntu VM from Phase 1. I added two Alpine containers as hosts on VLAN 100 so I could prove Layer 2 traffic actually makes it end to end across the overlay.

## Topology

```
               ┌───────────┐
               │  spine1   │  AS 65000 (underlay)
               │ 10.0.0.1  │  route reflector for EVPN
               └──┬─────┬──┘
       10.1.1.0/31│     │10.1.1.2/31
           ┌──────┘     └──────┐
     ┌─────┴─────┐       ┌─────┴─────┐
     │   leaf1   │       │   leaf2   │
     │ 10.0.0.11 │       │ 10.0.0.12 │
     │ AS 65001  │       │ AS 65002  │
     └─────┬─────┘       └─────┬─────┘
           │ Eth2, VLAN 100    │ Eth2, VLAN 100
     ┌─────┴─────┐       ┌─────┴─────┐
     │   host1   │       │   host2   │
     │10.100.100.11      │10.100.100.12
     └───────────┘       └───────────┘

  Overlay: all three run EVPN as AS 65100 (local-as), VNI 10100 <-> VLAN 100
  Management: 172.20.20.0/24 on bridge clab-mgmt
```

| Node | Mgmt IP | Loopback0 | Underlay ASN | Fabric links |
|---|---|---|---|---|
| spine1 | 172.20.20.11 | 10.0.0.1/32 | 65000 | Eth1 10.1.1.0/31, Eth2 10.1.1.2/31 |
| leaf1 | 172.20.20.21 | 10.0.0.11/32 | 65001 | Eth1 10.1.1.1/31, Eth2 access VLAN 100 |
| leaf2 | 172.20.20.22 | 10.0.0.12/32 | 65002 | Eth1 10.1.1.3/31, Eth2 access VLAN 100 |
| host1 | 172.20.20.101 | | | eth1 10.100.100.11/24 |
| host2 | 172.20.20.102 | | | eth1 10.100.100.12/24 |

## Design

- Underlay: eBGP on the /31 point-to-point links, one ASN per device. Each device advertises its loopback with a `network` statement. The spine sets `next-hop-self` toward the leaves so the reflected loopbacks resolve.
- Overlay: a second BGP session per leaf, loopback to loopback, carrying only the EVPN address family. All three devices present AS 65100 on these sessions with `local-as 65100 no-prepend replace-as`, so the overlay behaves like iBGP with spine1 as route reflector.
- Data plane: VXLAN, VLAN 100 mapped to VNI 10100. Each leaf sources VTEP traffic from Loopback0. RD is `<loopback>:10100`, route target `1:10100`, and `redistribute learned` exports the MACs the leaf learns on its access port.
- Result: Type-3 (IMET) routes build the flood list between VTEPs, and Type-2 (MAC/IP) routes carry host MACs. host1 can ping host2, and each leaf has the remote host's MAC in its VXLAN address table pointing at the other leaf's VTEP.

## Files

- `evpn-fabric.clab.yml`: topology. Pins the management bridge name to `clab-mgmt` and loads each router's startup config from `configs/`.
- `configs/spine1.cfg`, `configs/leaf1.cfg`, `configs/leaf2.cfg`: saved startup configs, so a fresh deploy comes up fully configured.
- `containerlab-evpn.service`: systemd unit that does a clean destroy and deploy on every boot of the lab VM.

## Deploy and destroy

```bash
sudo containerlab deploy  -t evpn-fabric.clab.yml
sudo containerlab inspect -t evpn-fabric.clab.yml
sudo containerlab destroy -t evpn-fabric.clab.yml --cleanup
```

Give it about 60 to 90 seconds after deploy for the cEOS agents to start and BGP to converge.

## Verify

```bash
docker exec clab-evpn-fabric-host1 ping -c 5 10.100.100.12

ssh admin@172.20.20.21          # leaf1, password admin
show bgp summary
show bgp evpn summary
show bgp evpn route-type mac-ip
show vxlan address-table
```

On leaf1 you should see two mac-ip routes: host1's MAC with RD 10.0.0.11:10100 (local) and host2's MAC with RD 10.0.0.12:10100, originator 10.0.0.12, cluster list 10.0.0.1. `show vxlan address-table` should list host2's MAC on Vx1 with VTEP 10.0.0.12.

## Auto-start on boot

```bash
sudo cp containerlab-evpn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now containerlab-evpn.service
```

The unit expects the lab in `/home/labadmin/evpn-lab`. Change the paths if you deploy from somewhere else.

## Lessons learned

- This was the hardest part of the whole lab. cEOS-lab would not carry EVPN routes across the eBGP overlay sessions, so the standard RFC 7938 eBGP-everywhere design didn't work on this image. Using `local-as 65100 no-prepend replace-as` on the EVPN peer group makes the overlay iBGP on top of the eBGP underlay. Real fabrics use the same idea (a separate overlay ASN), so it isn't just a lab hack.
- `Estab(NotNegotiated)` in the BGP summary means TCP is up but the address family was never activated on one side. Almost every time it was a missing `activate` or a typo in a peer group name.
- `next-hop-self` and next-hop-unchanged apply per address family. IPv4 needs `next-hop-self` on the spine so reflected loopbacks are reachable. EVPN needs the iBGP default (unchanged) so leaves build tunnels straight to each other and not to the spine.
- Type-2 routes need traffic from a real host port. I first tried pinging between SVIs on the leaves, but that never put anything in the bridge MAC table on cEOS-lab, so `redistribute learned` had nothing to send. Adding the Alpine hosts on access ports fixed it, and the SVIs came out of the final configs.
- `docker start` on a stopped cEOS container leaves it half broken (CLI and SSH hang). Always `containerlab destroy --cleanup` and deploy again. The systemd unit does this on boot.
- Without a `mgmt:` block Containerlab names the bridge `br-<random>` on every deploy. Pinning it to `clab-mgmt` keeps host tools pointed at the right interface.
- If an old lab left Docker's default `clab` network behind on 172.20.20.0/24, the deploy fails with "Subnet 172.20.20.0/24 already in use". Remove it with `docker network rm clab` once nothing is attached.
