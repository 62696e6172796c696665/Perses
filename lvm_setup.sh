#!/bin/sh

echo 0 > /sys/bus/pci/devices/0000:01:00.0/sriov_numvfs;
nvme virt-mgmt /dev/nvme0 -c 1 -a 7;
nvme virt-mgmt /dev/nvme0 -c 2 -a 7;

nvme virt-mgmt /dev/nvme0 -c 1 -r 0 -a 8 -n 2;
nvme virt-mgmt /dev/nvme0 -c 1 -r 1 -a 8 -n 2;
nvme virt-mgmt /dev/nvme0 -c 2 -r 0 -a 8 -n 2;
nvme virt-mgmt /dev/nvme0 -c 2 -r 1 -a 8 -n 2;


nvme virt-mgmt /dev/nvme0 -c 1 -a 9;
nvme virt-mgmt /dev/nvme0 -c 2 -a 9;

echo 2 > /sys/bus/pci/devices/0000\:01\:00.0/sriov_numvfs;

nvme delete-ns /dev/nvme0 -n 0xffffffff;

nvme create-ns /dev/nvme0 -s 0x2000000 -c 0x2000000 -f 0;
nvme attach-ns /dev/nvme0 -c 1 -n 1;
nvme create-ns /dev/nvme0 -s 0x2000000 -c 0x2000000 -f 0;
nvme attach-ns /dev/nvme0 -c 2 -n 2 ;

ls -l /sys/class/block/;