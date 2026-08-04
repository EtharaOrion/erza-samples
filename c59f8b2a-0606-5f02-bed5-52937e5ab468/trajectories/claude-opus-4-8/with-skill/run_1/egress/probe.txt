# Erza forced-no-net egress gate (post-install netns clamp)
container: df593ff6f9ec930b0583182ea74953433f0474ad79fa2f2bba990d02d4035ce6
image: erza-egress-fw:latest
bridge_port(probe): 8765

## native inspect (BEFORE rules)
# routes
default via 192.168.0.1 dev eth0 
192.168.0.0/20 dev eth0 scope link  src 192.168.0.2 
# route-get-v4
192.168.65.254 via 192.168.0.1 dev eth0  src 192.168.0.2 
# nc-192.168.65.254:8765
REACH
# hdi-resolve
192.168.65.254  STREAM host.docker.internal
192.168.65.254  DGRAM  host.docker.internal
# default-gw
gw=192.168.0.1

## firewall apply log
ERZA-FW-READY allow=[192.168.65.254 fdc4:f303:9324::254 ]

## two-sided probe (exit=0; PASS iff inet blocked & gateway ok)
inet=BLOCKED:URLError
gateway=OK:192.168.65.254
