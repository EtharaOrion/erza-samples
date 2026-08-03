# Erza forced-no-net egress gate (post-install netns clamp)
container: 4611ed84087ee24d358ab3954a3471da7e7904ca777ef7ad68f2eeaf66b4ac08
image: erza-egress-fw:latest
bridge_port(probe): 8765

## native inspect (BEFORE rules)
# routes
default via 172.20.0.1 dev eth0 
172.20.0.0/16 dev eth0 scope link  src 172.20.0.2 
# route-get-v4
192.168.65.254 via 172.20.0.1 dev eth0  src 172.20.0.2 
# nc-192.168.65.254:8765
REACH
# hdi-resolve
192.168.65.254  STREAM host.docker.internal
192.168.65.254  DGRAM  host.docker.internal
# default-gw
gw=172.20.0.1

## firewall apply log
ERZA-FW-READY allow=[192.168.65.254 fdc4:f303:9324::254 ]

## two-sided probe (exit=0; PASS iff inet blocked & gateway ok)
inet=BLOCKED:URLError
gateway=OK:192.168.65.254
