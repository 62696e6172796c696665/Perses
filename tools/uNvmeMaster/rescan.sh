#!/bin/sh
# Removes Boreas drive and rescans PCIe

if [ "$1" == "" ]; then
    echo "Usage (with root privileges): rescan.sh <bus#>"
    exit
fi
if [ "$(whoami)" != "root" ]; then
    echo "Need root privileges"
    exit
fi

echo 1 > /sys/bus/pci/devices/0000\:01\:00.0/remove
echo 1 > /sys/bus/pci/rescan

lspci | grep PLDA
lsmod | grep nvme
ls -l /dev/*nvme*