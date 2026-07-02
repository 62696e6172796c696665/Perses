cd c:\chaos
chaos -b=e: -t=4 -d=6 -g=4kb -s=64kb,512mb -m=4kb,64kb -p=1 -l=c:\chaos\chaos.log
rmdir /s /q e:\_chaos_
@echo Pass >> result.log
shutdown -r