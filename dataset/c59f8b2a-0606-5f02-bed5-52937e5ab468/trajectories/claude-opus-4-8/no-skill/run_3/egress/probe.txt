# Erza forced-no-net egress gate (post-install netns clamp)
container: d91d05ba8e88bcfab8194f3907970fcfc81400fe3db1ef538c6b06b9ea3a97bd
image: erza-egress-fw:latest
bridge_port(probe): 8765

## native inspect (BEFORE rules)
# routes
default via 172.29.0.1 dev eth0 
172.29.0.0/16 dev eth0 scope link  src 172.29.0.2 
# route-get-v4
192.168.65.254 via 172.29.0.1 dev eth0  src 172.29.0.2 
# nc-192.168.65.254:8765
REACH
# hdi-resolve
192.168.65.254  STREAM host.docker.internal
192.168.65.254  DGRAM  host.docker.internal
# default-gw
gw=172.29.0.1

## firewall apply log
ERZA-FW-READY allow=[192.168.65.254 fdc4:f303:9324::254 ]

## two-sided probe (exit=0; PASS iff inet blocked & gateway ok)
inet=BLOCKED:URLError
gateway=OK:192.168.65.254
