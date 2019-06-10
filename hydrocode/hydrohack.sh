ip link add hydrohack_in type veth peer name hydrohack_out
ip netns add hydrohack
ip link set dev hydroc netns hydrohack
ip link set dev hydrohack_in netns hydrohack
ip netns exec hydrohack ip addr add 192.168.22.2/24 dev hydrohack_in
ip addr add 192.168.22.1/24 dev hydrohack_out
ip netns exec hydrohack ip link set hydrohack_in up
ip link set hydrohack_out up
ip netns exec hydrohack ip addr add 192.168.91.93/24 broadcast 192.168.91.255 dev hydroc
ip netns exec hydrohack ip link set hydroc up

