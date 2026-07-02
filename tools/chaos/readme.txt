Huey Notes:

If you have a big LD size (> 200GB) use:  For ex:  chaos.exe -t=256 -f=128
 
If you have a small LD size (< 100GB) use:  For ex:   chaos.exe -t=256 -f=64

Following example commands for NVMe drive:
chaos -b=d: -g=4kb -s=4kb,2gb -m=4kb,128kb
for 1TB: large file, work ok
c:\chaos\chaos -b=e: -t=6 -d=8 -e=unique -g=4kb -s=4kb,1gb -m=4kb,512kb -p=1000 -l=c:\chaos\chaos.log

1TB: medium file size:
c:\chaos\chaos -b=e: -t=6 -d=8 -e=unique -g=4kb -s=4kb,256mb -m=4kb,64kb -p=1000 -l=c:\chaos\chaos.log


1TB: small file size:
c:\chaos\chaos -b=e: -t=6 -d=8 -e=unique -g=4kb -s=4kb,64mb -m=4kb,64kb -p=1000 -l=c:\chaos\chaos.log

chaos.exe -b=d: -o=both -t=6 -g=4kb -s=4kb,64mb -m=4kb,64kb -l=C:\Chaos\chaos.log -f=128

