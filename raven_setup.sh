#!/bin/sh
set -x
NVMECLICMD="nvme"
BDF="0000:01:00"
NUMVFS=2

echo 0 > /sys/bus/pci/devices/$BDF.0/sriov_numvfs
sleep 1
echo 0 > /sys/bus/pci/devices/$BDF.0/sriov_drivers_autoprobe
echo $NUMVFS > /sys/bus/pci/devices/$BDF.0/sriov_numvfs
echo 1 > /sys/bus/pci/devices/$BDF.0/sriov_drivers_autoprobe

sleep 2

$NVMECLICMD virt-mgmt /dev/nvme0 -c 1 -r 0x0 -a 0x8 -n 2
$NVMECLICMD virt-mgmt /dev/nvme0 -c 1 -r 0x1 -a 0x8 -n 2
echo 1 > /sys/bus/pci/devices/$BDF.1/reset
$NVMECLICMD virt-mgmt /dev/nvme0 -c 1 -a 0x9
echo $BDF.1 > /sys/bus/pci/drivers/nvme/bind

sleep 2

$NVMECLICMD virt-mgmt /dev/nvme0 -c 2 -r 0x0 -a 0x8 -n 2
$NVMECLICMD virt-mgmt /dev/nvme0 -c 2 -r 0x1 -a 0x8 -n 2
echo 1 > /sys/bus/pci/devices/$BDF.2/reset
$NVMECLICMD virt-mgmt /dev/nvme0 -c 2 -a 0x9
echo $BDF.2 > /sys/bus/pci/drivers/nvme/bind

sleep 2

$NVMECLICMD delete-ns /dev/nvme0 -n 0xffffffff;
$NVMECLICMD create-ns /dev/nvme0 -s 0x1000000 -c 0x1000000 -f 0;
$NVMECLICMD create-ns /dev/nvme0 -s 0x1000000 -c 0x1000000 -f 0;
$NVMECLICMD create-ns /dev/nvme0 -s 0x1000000 -c 0x1000000 -f 0;
sleep 2
$NVMECLICMD attach-ns /dev/nvme0 -c 0 -n 1;
sleep 2
$NVMECLICMD attach-ns /dev/nvme0 -c 1 -n 2;
sleep 2
$NVMECLICMD attach-ns /dev/nvme0 -c 2 -n 3 ;
sleep 2
ls -l /sys/class/block/;
