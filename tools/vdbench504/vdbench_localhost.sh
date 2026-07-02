#! /bin/bash
ip netns add netns
ip netns exec netns ip link set dev lo up
ip netns exec netns ./vdbench $*
ip netns delete netns