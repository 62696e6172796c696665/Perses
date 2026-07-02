[USAGE]
Linux:
	execute = ./uNvmeMaster
Windows:
    execute = uNvmeMaster.exe

; you can use [execute] without parameter to show help information
; if [command] is help, it will show the available command of the assigned [module]
; usually the format like the below
[execute] -d [drive ID] -m [module] -f [firmware version] -c [command] [parameter]

e.g:
Linux:
1.ScanSSD
./uNvmeMaster -m MFG -c ScanSSD

result:
...
[('/dev/nvme0', '0000:04:00.0', 'CVCQ522600BQ400AGN', 'INTEL SSDPEDMW400G4', 'ns number:1')]

2.Identify SSD controller:
./uNvmeMaster -d 0 -m NVME -c nvme_id_ctrl

windows:
1.ScanSSD
uNvmeMaster.exe -m MFG -c ScanSSD

result:
...
[('\\.\Scsi1:', 'CVCQ522600BQ400AGN', 'INTEL SSDPEDMW400G4', 'ns number:1')]

2.Identify SSD controller:
uNvmeMaster.exe -d 1 -m NVME -c nvme_id_ctrl

[Linux SMI SM2260 Example]
; configure directory: data/config/smi/2260/
; firmware directory: data/fw/smi/2260/
; generate binary file directory: data/fw/smi/2260/mptool

; This example is for 256GB
; Use configure file and fw bin package to initial, bin files are created by MPTool according to different capacity and have put to directory: such as "data/fw/smi/2260/fw_temp/256GB/"                   
1. ./uNvmeMaster -d 0 -m MFG -c smi_initial config=data/config/smi/2260/option_256GB.ini sn="123456789abcedfg"
Note: This command will do following Steps:
    S1: Download MPISP
    S2: Do Pretest
    S3: Download ISP

; Use configure file to initial, the advantage is you don't have to management a lot of bin files according to different capacity, T>B>D
2. ./uNvmeMaster -d 0 -m MFG -f 1126C-M -c smi_initial config=data/config/smi/2260/option_256GB.ini sn='' mn=''
; Use bin file to initial, you should known you bin file directory, different capacity has different bin files T>B>D

