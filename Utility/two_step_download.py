# coding=utf-8
#######################################################################################
#
# Unpublished Confidential Information of DellEMC Technology.
# Do not disclose.
# Copyright 2019 - DellEMC
#
# ALL RIGHTS RESERVED. These coded instructions and program statements are
# copyrighted works and confidential proprietary information of DellEMC Corp.
# They may not be modified, copied, reproduced, distributed, or disclosed to
# third parties in any manner, medium, or form, in whole or in part.
#
# Version Control Information:
#
# revision: 1.0
# comments: For redtail tahoe unbrick
# Author: Hao Fan
# Nov 1, 2019
#######################################################################################
import copy
import getpass
import logging
import os
import re
import sys
import time
import subprocess
import importlib
import yaml
import serial
import xmodem
import checksumdir
import logging.handlers
from pathlib import Path
import logaugment

sys.path.append("....")
sys.path.append("...")
sys.path.append("..")
sys.path.append(".")

currentPath = os.path.split(os.path.realpath(__file__))[0]
projectRootPath = os.path.abspath(os.path.join(currentPath, '..'))
utilPath = os.path.join(projectRootPath, 'util')
sys.path.append(projectRootPath)
sys.path.append(utilPath)
print("projectRootPath=%s" % projectRootPath)
print("currentPath=%s" % currentPath)
print("utilPath=%s" % utilPath)
print(sys.path)

from optparse import OptionParser
from serial.tools import list_ports
from lib.driver.test_framework.test_base import TestBase
from lib.driver.utils.ssh import SSH
from lib.driver.utils.system import get_root_path

download_main_fw_str = b"Waiting UART/JTAG..., please use XMODEM/J-LINK download:"
BOOT_ROM_FAIL_STR = b"ERROR - Booting from SPI has failed"

BL_IMAGE_INFO_FAIL_STR = b"loader:rom_validate_spi_image FAIL"
BL_FW_IMGAE_FAIL_STR = b"loader:rom_validate_spi_image FAIL"


PANIC_MODE_PC_STR = b"!!!Panic File Exists!!! pdupload or pderase !!!"
ASSERT_MODE_PC_STR = b"panic dump end."

UNSAFE_POWER_ON_STR = b"==> M30 unsafe power on completed <=="
SAFE_POWER_ON_STR = b"==> R5A safe power on completed <=="

MCP_COMPLETE = b"> MCP completed <"

TWO_STEP_EVENT_STR = "[TWO STEP EVENT]: "

class LoggerCreate():

    def __init__(self, path=None, name=None, signal=None, dut_name="", abs_path=None):
        self.signal = signal
        if abs_path:
            self.log_path = abs_path
        else:
            log_path1 = os.path.join(projectRootPath, "log")
            if not os.path.exists(log_path1):
                os.mkdir(log_path1)
            log_path = os.path.join(log_path1, path)
            if not os.path.exists(log_path):
                os.mkdir(log_path)
            self.log_path = log_path
        if not os.path.exists(self.log_path):
            os.mkdir(self.log_path)
        self.log_name = '{0}-{1}-{2}.log'.format(
            time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())),
            dut_name, name.split('.')[0]
        )
        print("log_path---" + self.log_path)
        print("log_name---" + self.log_name)
        self.log_file = os.path.join(self.log_path, self.log_name)
        # clear all default handlers
        default_handlers = logging.getLogger().handlers
        if len(default_handlers):
            for handler in default_handlers:
                logging.getLogger().removeHandler(handler)

        # create a new logger object
        self.logger = logging.getLogger("test-platform2.0")
        self.logger.propagate = False
        self.logger.setLevel(logging.INFO)

        self.formatter = logging.Formatter('[%(device)s] %(asctime)s - %(levelname)s '
                                           '- %(filename)s[line:%(lineno)d] '
                                           '- %(message)s')
        # remove the existing handlers ( possibly no handlers here )
        if self.logger.handlers:
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        self.ch = logging.StreamHandler()
        self.ch.setFormatter(self.formatter)
        logaugment.set(self.logger, device=str(dut_name))
        self.logger.addHandler(self.ch)

        if self.logger.handlers:
            for handler in self.logger.handlers:
                handler.setFormatter(self.formatter)


    def add_file_handler(self):
        #  fh = logging.FileHandler(self.log_file, mode='a+')
        fh = logging.handlers.WatchedFileHandler(self.log_file, encoding="utf-8", delay=False)
        fh.setLevel(logging.INFO)
        fh.setFormatter(self.formatter)
        self.logger.addHandler(fh)

    def get_log(self):
        """return instance"""
        return self.logger


def create_logger( drive_name ):
    logger_obj = LoggerCreate("Two_step", "two_step_download-" + options.serialPort)
    logger_obj.add_file_handler()
    return logger_obj

class TwoStepDownload(TestBase):
    ROM_BAUDRATE = 115200
    DNLD_BAUDRATE = 115200
    FW_BAUDRATE = 115200
    PUTTY_PATH = r"C:\putty\PUTTY-CNEX-VER1.5.3.exe"
    TERA_TERM_PATH = r"C:\Program Files (x86)\teraterm\ttermpro.exe"
    TERA_TERM = "ttermpro.exe"
    POWER_OFF_WAIT = 8
    MAX_POWER_ON_COM_WAIT = 15
    MAX_POWER_ON_LOG_TIME = 180
    MAX_FW_SAVE_TIME = 450
    FW_UART_RESP_SUFFIX_STR = b"UART>"
    DRIVE_STATUS_UNKNOWN = 0
    DRIVE_IN_BOOT_ROM = 1
    DRIVE_IN_BOOT_LOADER = 2
    DRIVE_IN_MAIN_FW = 3
    DRIVE_IN_SPI_APP = 4
    DRIVE_IN_NEW_FW = 5
    DRIVE_IN_PANIC_MODE = 6
    DRIVE_IN_ASSERT_MODE = 7

    def __init__(self, oakgate, iroc, serialPort, preBinPath, firmwarePath,
                 control_serial=False, logger=None, allow_reboot=False, dlfw_tried=False, firmwarePathBin=None):
        super().__init__()
        self.logger = logger
        self.oakgate = oakgate
        self.iroc = iroc
        self.serialPort = serialPort.strip()
        self.preDnldBin = preBinPath
        self.firmwarePath = firmwarePath
        self.firmwarePathBin = firmwarePathBin
        self.powerOnHandle = None
        self.powerOffHandle = None
        self.isNeedOpenSerial = False
        self.binFwVerStr = self.getFwCommitIdFromFwBinary()
        self.control_serial = control_serial
        self.device = None
        self.mcp_required = True
        self.allow_reboot = allow_reboot
        self.dlfw_tried = dlfw_tried
        self.target_ip = self.iroc
        self.slot = os.environ.get("slot", 'None')
        self.user = os.environ.get('user', 'root')
        self.password = os.environ.get('password', 'nvme')
        self.commit = os.environ.get('commit', 'no_set')
        #self.adapter = os.environ.get('adapter', 'cp20')
        self.adapter = os.environ.get('adapter', None)
        #self.quarch_dev_str = os.environ.get('quarch', 'SERIAL:/dev/ttyUSB0')  # SERIAL:/dev/ttyUSB0
        self.quarch_dev_str = os.environ.get('quarch', None)
        self.cnextb_dev_str = os.environ.get('cnextb', None)
        self.ssh = SSH(self.target_ip, username=self.user, password=self.password)
        self.ssh.open()
        self.ssh.command("mount -a")
        self.remote_env_path = self.get_remote_path()
        self.remote_env_perses_path = "{}/{}".format(self.remote_env_path, "perses")
        self.local_env_perses_path = get_root_path()
        self.setup_target_environment()
        print("self.iroc")
        print(self.iroc)
        print("self.quarch_dev_str")
        print(self.quarch_dev_str)
        print("self.cnextb_dev_str")
        print(self.cnextb_dev_str)
        print("self.commit")
        print(self.commit)
        print("self.adapter")
        print(self.adapter)

    def load_platform_lib(platform):
        for file_path in Path(os.path.join('Platform', platform, 'library')).glob('**/[!__]*.py'):
            tmp_module_platform = '.'.join(str(file_path).split(os.sep))[:-3]
            tmp_module_target = 'Core_lib' + tmp_module_platform.split('library')[-1]
            sys.modules[tmp_module_target] = importlib.import_module(tmp_module_platform)

    def rescan_system(oak_obj):
        client = RestClient(oak_obj['ip_addr'] + ":9998")
        disco_system = None
        subnets = oak_obj['sub_net']
        system_name = oak_obj['sys_name']
        try:
            client.finder.set_subnets(subnets)
            client.finder.scan_subnets()
        except Exception as _:
            client.finder.set_subnets(subnets)
            client.finder.scan_subnets()
        time.sleep(2)
        for system in client.finder.get_discovery_system_collection():
            if system.name == system_name:
                disco_system = system
                break
        return disco_system

    def reboot_oak_sys(oak_obj, logger=None):
        client = RestClient(oak_obj['ip_addr'] + ":9998")
        disco_system = rescan_system(oak_obj)
        logger.warning("Reboot OAKGATE %s now, it will take about 10min" % oak_obj["sys_name"])
        client.finder.reboot_discovery_system(disco_system.uid)
        start_time = time.time()
        while rescan_system(oak_obj):
            if start_time - time.time() > 120:
                raise Exception("Can't reboot system %s" % oak_obj["sys_name"])
            time.sleep(5)
        while time.time() - start_time < 600:
            disco_sys = rescan_system(oak_obj)
            if disco_sys:
                logger.info("System %s is back" % oak_obj["sys_name"])
                return disco_sys
            logger.info("Wait 60s for system reboot")
            time.sleep(60)
        else:
            raise Exception("Can't disco system %s after waiting for 10min" % oak_obj["sys_name"])


    def print_event(self, msg):
        msg = TWO_STEP_EVENT_STR + msg
        self.logger.info(msg)

    def get_remote_path(self):
        network_path = r"/home/nvme/SQA/powercycle"
        if self.ssh.is_exist(network_path):
            remote_path = r"/home/nvme/SQA/powercycle/{}".format(self.target_ip)
        else:
            remote_path = r"/home/powercycle"
        return remote_path

    def remote_install(self, remote_path):
        command = "cd {} && python install.py".format(remote_path)
        status, output = self.ssh.command(command)
        if status != 0:
            print("remotes install failed")
        print(output)
        return status, output

    def dos2unix(self, remote_path):
        paths = ["{}/tools/fio".format(remote_path),
                 "{}/tools/vdbench504".format(remote_path),
                 "{}/tools/usbrelay".format(remote_path)]
        for item in paths:
            command = "cd {} && dos2unix *".format(item)
            status, output = self.ssh.command(command)
            if status != 0:
                print("dos2unix {} install failed".format(item))
            print(output)

    def chmod_files(self, remote_path):
        paths = ["{}/tools/fio/fio".format(remote_path),
                 "{}/tools/vdbench504/vdbench".format(remote_path),
                 "{}/tools/usbrelay/usbrelay".format(remote_path)]
        for item in paths:
            command = "chmod 777 {}".format(item)
            status, output = self.ssh.command(command)
            if status != 0:
                print("chmod  {}  failed".format(item))
            print(output)

    def setup_target_environment(self):
        ret = self.ssh.is_exist(self.remote_env_perses_path)
        if ret is False:
            self.upload_and_init_perses_2_target()
        else:
            self.update_modified_perses_2_target()
            self.update_run_file()

    def upload_and_init_perses_2_target(self):
        if self.ssh.is_exist(self.remote_env_path) is False:
            self.ssh.make_dir(self.remote_env_path)
        if self.ssh.is_exist(self.remote_env_perses_path) is False:
            self.ssh.make_dir(self.remote_env_perses_path)
        self.ssh.sftp_put_dir(self.local_env_perses_path, self.remote_env_perses_path)
        self.remote_install(self.remote_env_perses_path)
        self.dos2unix(self.remote_env_perses_path)
        self.chmod_files(self.remote_env_perses_path)

    def update_modified_perses_2_target(self):
        try:
            compare_folder = ["testfile", "configuration", "lib", "testcase", "testsuite"]
            for folder in compare_folder:
                local_path = os.path.join(self.local_env_perses_path, folder)
                remote_path = r"{}/{}".format(self.remote_env_perses_path, folder)
                local_md5 = self.get_folder_md5(local_path)
                remote_md5 = self.get_folder_md5_by_ssh(remote_path)
                if local_md5 != remote_md5:
                    temp_path = "{}/{}".format(self.remote_env_perses_path, folder)
                    self.ssh.command("rm -rf {}".format(temp_path))
                    self.ssh.make_dir(temp_path)
                    self.ssh.sftp_put_dir(local_path, temp_path)
            self.dos2unix(self.remote_env_perses_path)
        except Exception as exceptions:
            self.print_event("exceptions {}".format(exceptions))

    def get_folder_md5(self, path):
        md5hash = None
        if os.path.exists(path):
            md5hash = checksumdir.dirhash(path, 'md5', excluded_extensions=['pyc'])
        return md5hash

    def get_folder_md5_by_ssh(self, path):
        md5 = None
        cmd = "checksumdir {} -a md5 -x pyc".format(path)
        status, output = self.ssh.command(cmd)
        if status == 0:
            md5 = output.replace("\n", "")
        return md5

    def update_run_file(self):
        local_path = os.path.join(self.local_env_perses_path, "run.py")
        remote_path = r"{}/{}".format(self.remote_env_perses_path, "run.py")
        self.ssh.command("rm -r {}".format(remote_path))
        self.ssh.sftp_put(local_path, remote_path)

    def exec_ssh_cmd(self, cmd, timeout=None):
        self.logger.info("Execute SSH command: " + cmd)
        status, output = self.ssh.command(cmd, timeout=timeout)
        self.logger.info(output)
        return status, output

    def restart_drive_iroc(self):
        if self.iroc:
            from core.PcpClient.PcpClient import PcpClient
            from iguana.engine.common import get_guids_by_name_w_slice

            load_platform_lib(platform)
            iroc_info = self.iroc.split(":")
            if len(iroc_info) < 3:
                iroc_info.append(9734)
            ip, drive_num, port = iroc_info
            iroc_client = PcpClient(ip, port)
            device_name = "Drive " + str(drive_num)
            drives = get_guids_by_name_w_slice(ip, device_name, 5, 0)

            if not drives:
                raise Exception("Cannot find target drive: {}.".format(device_name))
            self.logger.info("The target drive {}, UID list {}".format(drive_num, drives))

            # Make the parent device to be the last one.
            drives.reverse()
            iroc_client.guids_pool = copy.deepcopy(drives)

            iroc_client.automic.nvme_restart_drive()
            self.logger.info("Restart drive successfully")

    def getFwCommitIdFromFwBinary(self):
        verStr = ""
        if self.firmwarePathBin:
            fwFile = open(self.firmwarePathBin, "rb")
            fwStr = fwFile.read(-1)
            fwFile.close()
            findVerStrList = re.findall(br"t [0-9a-f]{40}", fwStr)
            if len(findVerStrList) == 1:
                verStr = findVerStrList[0].split(b" ")[-1].strip()
            else:
                verStr = b""
            self.logger.info("from firmware binary commit id is: %s" % verStr.decode("ascii"))
        return verStr

    def preDownloadCheck(self):
        if os.name == "nt":
            if self.iroc:
                self.exec_ssh_cmd("nvme list")
                status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                if 'No such file or directory' in cmd_ret:
                    dev_cnt = 0
                else:
                    dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                    dev_cnt_list = set(dev_all_cnt)
                    dev_cnt = len(dev_cnt_list)
                self.logger.info('find {} nvme device'.format(dev_cnt))
                #if self.quarch_dev_str and "SERIAL:/dev/ttyUSB" in self.quarch_dev_str:
                if self.quarch_dev_str:
                    quarch_poweron_str = "RUN:POWer UP"
                    quarch_poweroff_str = "RUN:POWer DOWN"
                    quarch_cmd_poweron_str = 'python -c "from quarchpy.device import * ; ' \
                                             'from quarchpy.disk_test.driveTestCore import executeAndCheckCommand;' \
                                             'temp= quarchDevice(\'{}\');' \
                                             'executeAndCheckCommand(temp, \'{}\')"'.format(self.quarch_dev_str,
                                                                                            quarch_poweron_str)
                    quarch_cmd_poweroff_str = 'python -c "from quarchpy.device import * ; ' \
                                              'from quarchpy.disk_test.driveTestCore import executeAndCheckCommand;' \
                                              'temp= quarchDevice(\'{}\');' \
                                              'executeAndCheckCommand(temp, \'{}\')"'.format(self.quarch_dev_str,
                                                                                             quarch_poweroff_str)
                    self.powerOffHandle = lambda: self.exec_ssh_cmd(quarch_cmd_poweroff_str)
                    time.sleep(self.POWER_OFF_WAIT)
                    self.powerOnHandle = lambda:self.exec_ssh_cmd(quarch_cmd_poweron_str)
                elif self.cnextb_dev_str:
                    cnextb_poweron_str = "RUN:POWer UP"
                    cnextb_poweroff_str = "RUN:POWer DOWN"
                    cnextb_cmd_poweron_str = 'python -c "from cnextb.device import * ; ' \
                                             'temp= CnextbDevice(\'{}\');' \
                                             'executeAndCheckCommand(temp, \'{}\')"'.format(self.cnextb_dev_str,
                                                                                            cnextb_poweron_str)
                    cnextb_cmd_poweroff_str = 'python -c "from cnextb.device import * ; ' \
                                              'temp= CnextbDevice(\'{}\');' \
                                              'executeAndCheckCommand(temp, \'{}\')"'.format(self.cnextb_dev_str,
                                                                                             cnextb_poweroff_str)
                    self.powerOffHandle = lambda: self.exec_ssh_cmd(cnextb_cmd_poweroff_str)
                    time.sleep(self.POWER_OFF_WAIT)
                    self.powerOnHandle = lambda:self.exec_ssh_cmd(cnextb_cmd_poweron_str)
                else:
                    power_on_str = "cd /home/share/sqa/xyang/perses/lib/tool/cp210x/;python3 cp210x.py -p  1"
                    power_off_str = "cd /home/share/sqa/xyang/perses/lib/tool/cp210x/;python3 cp210x.py -p  0"
                    self.powerOffHandle = lambda: self.exec_ssh_cmd(power_off_str)
                    time.sleep(self.POWER_OFF_WAIT)
                    self.powerOnHandle = lambda: self.exec_ssh_cmd(power_on_str)
                    time.sleep(2)
                    self.reboot()
                    result = self.wait_reboot_complete()
                    self.logger.info("Reboot complete:{}".format(result))
                self.exec_ssh_cmd("nvme list")
                status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                if 'No such file or directory' in cmd_ret:
                    dev_cnt = 0
                else:
                    dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                    dev_cnt_list = set(dev_all_cnt)
                    dev_cnt = len(dev_cnt_list)
                self.logger.info('find {} nvme device'.format(dev_cnt))
            try:
                ser = self.power_cycle_uart()
            except Exception as e:
                self.logger.info("Failed to open serial port %s, will again" % self.serialPort)
                portList = [portInfo.device for portInfo in list_ports.comports()]
                if self.serialPort not in portList:
                    raise ValueError("Invalid Serial port %s, actual is %s" % (self.serialPort, portList))
                self.checkSerialPortWindows()
                time.sleep(5)
                ser = self.power_cycle_uart()
            finally:
                ser.close()
        else:
            raise EnvironmentError("Can't support os type %s, please add that" % os.name)

    def postDownloadCheck(self):
        if os.name == "nt":
            if self.isNeedOpenSerial:
                self.openSerialWindows(log_path=options.logPath)
        else:
            raise EnvironmentError("Can't support os type %s, please add that" % os.name)

    def checkSerialPortWindows(self):
        """
        @return: if Serial is in use return True, else return False
        """
        print("checkSerialPortWindows")
        time.sleep(2)       # Ensure tera term get serial port
        chkPortCmdStr = "wmic process where \"Name like '%%ttermpro.exe%%'\" get CommandLine,ProcessId"
        cmdRun = subprocess.run(args=chkPortCmdStr, stdout=subprocess.PIPE)
        matchLines = cmdRun.stdout.strip().split(b"\n")
        if len(matchLines) == 0:
            self.logger.info("No open ttermpro.exe process")
            return False

        lines = cmdRun.stdout.strip().split(b"\n")[1:]
        com_arg = "/C=" + self.serialPort.replace("COM", "")
        self.logger.info("Name like ttermpro.exe process: %s " %lines)
        for line in lines:
            line = line.strip().decode("utf-8")
            pid = line.split()[-1]
            if "/C=" not in line:
                self.logger.info("Kill ttermpro.exe process PID: %s " % (pid))
                os.system("taskkill /F /PID %s" % pid)
            elif com_arg in line:
                self.logger.info("Kill process %s PID is %s" % (self.serialPort, pid))
                os.system("taskkill /F /PID %s" % pid)
                return True
        return False

    def openSerialWindows(self, log_path=None):
        if self.oakgate:
            drive_name = self.oakgate
        elif self.iroc:
            drive_name = self.iroc
        iniPath = os.path.join(os.path.split(self.TERA_TERM_PATH)[0], "TERATERM.INI")
        serialNumber = self.serialPort.replace("COM", "")
        if log_path is None:
            log_path = os.path.join(projectRootPath, "log", "UART_LOG")
        if os.path.exists(log_path) is False:
            os.makedirs(log_path)
        time_str = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        log_name = "_".join(["UART", drive_name, self.serialPort, time_str])
        log_name = os.path.join(log_path, log_name)
        self.logger.info("UART_log name: %s" % log_name)
        self.print_event("Reopen TeraTerm start")

        cmdStr = 'start "" "%s" /C=%s /BAUD=%s /F="%s" /L=%s'% (
            self.TERA_TERM_PATH, serialNumber, self.FW_BAUDRATE, iniPath, log_name
        )
        self.print_event("Reopen TeraTerm done...")
        self.print_event("cmd = " + cmdStr)
        os.system(cmdStr)

    def xmodemSendFile(self, serialPort, baudrate, filePath, waitPattern=b"", maxWaitTime=2):
        if baudrate == self.ROM_BAUDRATE:
            BASE_PKG_ITV = 10e-3  # 10ms for ROM code, packet interval 10ms will have none packet error
        else:
            BASE_PKG_ITV = 3.2e-3  # 3.2ms for pre download FW, packet interval 10ms will have none packet error
        PKG_ITV_INC = 0.2e-3  # 0.2ms
        MAX_PKG_ITV = 10e-3  # max 10ms delay
        fileSize = os.path.getsize(filePath)
        argumentDict = {"currentInterval": BASE_PKG_ITV, "intervalInc": PKG_ITV_INC, "maxInterval": MAX_PKG_ITV,
                        "fileSize": fileSize, "totalErrorCount": 0}
        ser = serial.Serial(port=serialPort, baudrate=baudrate)
        startTime = time.time()  # Wait an vaild xmodem char
        while True:
            if ser.read() in [xmodem.NAK, xmodem.CRC, xmodem.CAN]:
                self.logger.info("UART in XMODEM mode, download costs about 7min")
                break
            if time.time() - startTime >= 6:
                return False

        def getc(size, timeout=1):
            ser.timeout = timeout
            return ser.read(size)

        def putc(data, timeout=1, argumentDict=argumentDict):
            ser.write_timeout = timeout
            retVal = ser.write(data)
            time.sleep(argumentDict["currentInterval"])
            return retVal

        def callback(total_packets, success_count, error_count, argumentDict=argumentDict):
            if error_count and argumentDict["currentInterval"] < argumentDict["maxInterval"]:
                argumentDict["currentInterval"] += argumentDict["intervalInc"]
                argumentDict["totalErrorCount"] += 1
            percentStr = "Download Progress: >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>||"
            printStr = ""
            if total_packets == 1:
                argumentDict["totalPacket"] = argumentDict["fileSize"] // 128
                if argumentDict["fileSize"] % 128:
                    argumentDict["totalPacket"] += 1
                argumentDict["totalProgressSymbol"] = percentStr.count(">")
                argumentDict["printedSymbolCount"] = 0
                argumentDict["printedIndex"] = percentStr.index(">")
                printStr += percentStr[:argumentDict["printedIndex"]]
            elif success_count < argumentDict["totalPacket"]:
                symbolCount = argumentDict["totalProgressSymbol"] * success_count // argumentDict["totalPacket"]
                if symbolCount > argumentDict["printedSymbolCount"]:
                    needPrintSymbolCnt = symbolCount - argumentDict["printedSymbolCount"]
                    argumentDict["printedSymbolCount"] += needPrintSymbolCnt
                    argumentDict["printedIndex"] += needPrintSymbolCnt
                    printStr += percentStr[
                                argumentDict["printedIndex"]: argumentDict["printedIndex"] + needPrintSymbolCnt]
            else:
                printStr += percentStr[argumentDict["printedIndex"]:] + "\n"
                total_packets = argumentDict["totalErrorCount"] + success_count
                errorRate = float(argumentDict["totalErrorCount"]) // total_packets
                printStr += ("total_packets=%d, success_count=%d, currentInterval=%.1fms, errorRate=%.1f%%\n" %
                             (total_packets, success_count, argumentDict["currentInterval"] * 1000, errorRate * 100))
            if printStr:
                sys.stdout.write(printStr)

        xmd = xmodem.XMODEM(getc, putc)
        with open(filePath, "rb") as inFile:
            startTime = time.time()
            xmd.send(inFile, retry=128, callback=callback)
            endTime = time.time()
            transferSpeedInKiB = argumentDict["fileSize"] / 1024.0 / (endTime - startTime)
            self.logger.info("Transfer speed is %.1fKiB/s" % transferSpeedInKiB)
        receiveStr = b""
        ser.timeout = 0.2
        if waitPattern:
            checkLength = len(waitPattern)
            startTime = time.time()
            while True:
                receiveChar = ser.read()
                if receiveChar:
                    receiveStr += receiveChar
                    sys.stdout.write(receiveChar.decode("ascii", "ignore"))
                    checkStr = receiveStr[-checkLength:]
                    if waitPattern == checkStr:
                        ser.timeout = 2
                        self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                        break
                if time.time() - startTime > maxWaitTime:
                    break
        else:
            startTime = time.time()
            while startTime - time.time() < maxWaitTime:
                receiveChar = ser.read()
                receiveStr += receiveChar
                sys.stdout.write(receiveChar.decode("ascii", "ignore"))
        ser.close()
        return receiveStr

    def powerCycleGetDriveStatus(self):
        self.logger.info("Power cycle to get drive status")
        ser = self.power_cycle_uart()
        # checkLength = max(len(BOOT_ROM_FAIL_STR), len(BL_IMAGE_INFO_FAIL_STR), len(BL_FW_IMGAE_FAIL_STR),
        #                   len(FW_ASSERT_PREFIX_STR), len(SAFE_POWER_ON_STR), len(MCP_COMPLETE))
        checkLength = max(len(BOOT_ROM_FAIL_STR), len(BL_IMAGE_INFO_FAIL_STR), len(BL_FW_IMGAE_FAIL_STR),
                          len(SAFE_POWER_ON_STR), len(MCP_COMPLETE))

        logStr = b""
        startTime = time.time()
        driveStatus = self.DRIVE_STATUS_UNKNOWN
        while True:
            readChar = ser.read(1)
            if readChar:
                logStr += readChar
                sys.stdout.write(readChar.decode("ascii", "ignore"))
                checkStr = logStr[-checkLength:]
                if BOOT_ROM_FAIL_STR in checkStr:
                    self.logger.info("Drive in boot rom, bootloader failed")  #b"ERROR - Booting from SPI has failed"
                    driveStatus = self.DRIVE_IN_BOOT_ROM
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
                if BL_IMAGE_INFO_FAIL_STR in checkStr or BL_FW_IMGAE_FAIL_STR in checkStr:  #b"loader:rom_validate_spi_image FAIL"
                    self.logger.info("Drive in bootloader")
                    driveStatus = self.DRIVE_IN_BOOT_LOADER
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
                if MCP_COMPLETE in checkStr:            #b"> MCP completed <"
                    self.logger.info("Drive in main FW, MCP is also done")
                    driveStatus = self.DRIVE_IN_MAIN_FW
                    self.mcp_required = False
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
                if PANIC_MODE_PC_STR in logStr: #b"!!!Panic File Exists!!! pdupload or pderase !!!"
                    self.logger.info("Drive in main FW and drive is in panic mode")
                    driveStatus = self.DRIVE_IN_PANIC_MODE
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
                if ASSERT_MODE_PC_STR in logStr: #b"panic dump end."
                    self.logger.info("Drive in main FW and drive met ASSET, panic file dumped")
                    driveStatus = self.DRIVE_IN_ASSERT_MODE
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
                if UNSAFE_POWER_ON_STR in logStr:  #b"==> M30 unsafe power on completed <=="
                    self.logger.info("Drive in main FW, and unsafe power on complete")
                    driveStatus = self.DRIVE_IN_MAIN_FW
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    break
            if readChar == b"\x15":
                self.logger.info("Check if UART is in ROM without output")
                if self.isDriveInUartDnld(self.ROM_BAUDRATE, nakInterval=5, ser=ser):
                    self.logger.info("SSD is in ROM mode")
                    driveStatus = self.DRIVE_IN_BOOT_ROM
                    break
            if time.time() - startTime > self.MAX_POWER_ON_LOG_TIME:
                self.logger.info("Fail to identify SSD status from UART")
                break
        ser.close()
        if driveStatus == self.DRIVE_STATUS_UNKNOWN and self.isDriveInFirmware():
            self.logger.info(logStr.decode("ascii", "ignore"))
            self.logger.info("Drive status is unknow, UART is active")
            driveStatus = self.DRIVE_IN_MAIN_FW

        return driveStatus

    def sendUartCmd(self, ser, cmdStr, waitPattern=FW_UART_RESP_SUFFIX_STR, timeout=None):
        if not ser.is_open:
            ser.open()
        ser.flushInput()
        ser.write(b"\n")
        self.logger.info(ser.read_until(self.FW_UART_RESP_SUFFIX_STR).decode("ascii"))
        for ch in cmdStr:
            ser.write(bytes([ch]))
            sys.stdout.write(ser.read_until(bytes([ch])).decode("ascii"))
        ser.write(b"\n")
        if timeout is not None:
            originTimeout = ser.timeout
            ser.timeout = timeout
        responseStr = ser.read_until(waitPattern)
        #  sys.stdout.write(responseStr.decode("ascii"))
        try:
            self.logger.info(responseStr.decode("ascii"))
        except Exception as e:
            self.logger.warning(e)
        if timeout is not None:
            ser.timeout = originTimeout
        return responseStr

    def getFwCommitIdFromUart(self):
        ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE, timeout=5)
        responseStr = self.sendUartCmd(ser, b"ver")
        ser.close()
        findStrList = re.findall(b"GIT Commit +: +commit +[0-9a-f]{40}", responseStr)
        assert len(findStrList) == 1
        return findStrList[0].split(b" ")[-1]

    def do_uart_process_with_pc(self, process_name, max_wait_time=120, ser=None):
        if not ser:
            ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE, timeout=5)

        process_dict = {
            "mcp": {
                "process_cmd": b"clearspi 1",
                "expected_pattern_before_pc": b"clearspi complete",
                "expected_pattern_after_pc": SAFE_POWER_ON_STR
            },
        }

        self.print_event(process_name + " flow start")
        process = process_dict[process_name]
        time.sleep(2)

        time.sleep(5)
        try:
            self.sendUartCmd(
                ser, process["process_cmd"],
                waitPattern=process["expected_pattern_before_pc"],
                timeout=max_wait_time
            )
        except Exception:
            self.sendUartCmd(
                ser, process["process_cmd"],
                waitPattern=process["expected_pattern_before_pc"],
                timeout=max_wait_time
            )
        finally:
            ser.close()

        self.logger.info("Start to do power cycle after command {}".format(process_name))
        ser = self.power_cycle_uart()
        complete_indicator = process["expected_pattern_after_pc"]
        checkLength = len(complete_indicator)
        logStr = b""
        startTime = time.time()
        while True:
            readChar = ser.read(1)
            if readChar:
                try:
                    sys.stdout.write(readChar.decode("ascii", "ignore"))
                    logStr += readChar
                except Exception as e:
                    self.logger.warning(e)
                checkStr = logStr[-checkLength:]
                if complete_indicator in checkStr:
                    ser.timeout = 2
                    sys.stdout.write(ser.read(0xFFFF).decode("ascii", "ignore"))
                    self.print_event("{} flow succeeded".format(process_name))
                    break
            if time.time() - startTime > max_wait_time:
                self.print_event("{} flow timeout after {}s".format(process_name, max_wait_time))
                break
        ser.close()
        time.sleep(10)
        self.logger.info(logStr.decode("ascii", "ignore"))
        return complete_indicator in checkStr

    def power_cycle_uart(self):
        self.powerOffHandle()
        time.sleep(self.POWER_OFF_WAIT)
        self.powerOnHandle()
        # open serial port
        startTime = time.time()
        self.logger.info("Start to identify UART port ")
        while True:
            try:
                ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE, timeout=5)
                break
            except Exception as e:
                if time.time() - startTime > self.MAX_POWER_ON_COM_WAIT:
                    raise EnvironmentError(
                        "Can't find %s port after power on %ds ERROR=%s" %
                        (self.serialPort, self.MAX_POWER_ON_COM_WAIT, e))
            time.sleep(0.1)
        self.logger.info("UART port is back after power on")
        time.sleep(1)
        return ser

    def forceEnterBlBfbk(self):
        self.print_event("Force enter bootloader")
        self.logger.info("Start to force entering bootloader with 20 spaces")
        ser = self.power_cycle_uart()
        # check received message
        FORCE_FBBK_STR = b"Receive 20 spaces, press enter to erase"
        checkLength = len(FORCE_FBBK_STR)
        logStr = b""
        startTime = time.time()
        driveStatus = self.DRIVE_STATUS_UNKNOWN
        while True:
            ser.write(b" ")
            readStr = ser.read(ser.in_waiting)
            if readStr:
                logStr += readStr
                sys.stdout.write(readStr.decode("ascii", "ignore"))
                if FORCE_FBBK_STR in logStr:
                    driveStatus = self.DRIVE_IN_BOOT_LOADER
                    ser.timeout = 2
                    self.logger.info(ser.read(0xFFFF).decode("ascii", "ignore"))
                    self.print_event("Force enter bootloader succeeded")
                    break
                logStr = logStr[-checkLength:]
            if time.time() - startTime > self.MAX_POWER_ON_LOG_TIME:
                msg = "Force enter bootloader timeout after {}s".format(self.MAX_POWER_ON_LOG_TIME)
                self.print_event(msg)
                break
        ser.close()
        return driveStatus

    def eraseBootloaderInBl(self):
        self.print_event("Start to erase bootloader ")
        ser = serial.Serial(port=self.serialPort, baudrate=self.ROM_BAUDRATE, timeout=0.1)
        ser.flushInput()
        # Send 20 space follow an enter tell drive erase bootloader
        ERASE_SYNC_STR = b"press enter to erase:"
        checkLength = len(ERASE_SYNC_STR)
        logStr = b""
        startTime = time.time()
        while True:
            readStr = ser.read(0xFFFF)
            if readStr:
                logStr += readStr
                sys.stdout.write(readStr.decode("ascii", "ignore"))
                if ERASE_SYNC_STR in logStr:
                    ser.timeout = 1
                    ser.write(b"\n")
                    self.logger.info(
                        ser.read_until(b"power cycle drive will enter ROM mode....").decode("ascii", "ignore"))
                    #  sys.stdout.write(
                        #  ser.read_until(b"power cycle drive will enter ROM mode....").decode("ascii", "ignore"))
                    ser.close()
                    self.print_event("Erase bootloader succeeded")
                    return True
                else:
                    logStr = logStr[-checkLength:]
            else:
                ser.write(b" ")
            if time.time() - startTime > self.MAX_POWER_ON_LOG_TIME:
                msg = "Erase bootloader timeout after {}s".format(self.MAX_POWER_ON_LOG_TIME)
                self.print_event(msg)
                return False

    def close_serial_port(self):
        self.print_event("Kill Teraterm and PUTTY processes")
        os.system("taskkill /F /IM ttermpro.exe")
        os.system("taskkill /F /FI \"IMAGENAME eq PUTTY*\"")

    def open_serial_port(self):
        self.print_event("Open Teraterm")
        subprocess.Popen(['C:\\Program Files (x86)\\ttermpro\\ttermpro.exe'])

    def command_without_result(self, cmd, cmdline=True, timeout=None):
        if cmdline:
            self.logger.info(cmd)
        if not self.is_active():
            self.open()
            self.logger.info("try to open ssh, status now: %s", self.is_active())
        self._ssh.exec_command(cmd, timeout=timeout)

    def reboot(self):
        self.logger.info("reboot......")
        try:
            self.ssh.command_without_result("reboot -nf", timeout=10)
        except Exception:
            self.logger.info("execute reboot command failed, try again")
            self.ssh.open(timeout=10)
            self.ssh.command_without_result("reboot -nf", timeout=10)
        time.sleep(10)
        self.ssh.close()

    def wait_reboot_complete(self, time_out=600):
        result = False
        start_time = time.time()
        current_time = start_time
        duration = current_time - start_time
        while duration < time_out:
            self.logger.info("try to connect target compute: time %s", duration)
            try:
                self.ssh.open(timeout=10)
            except Exception:
                pass
            if self.ssh.is_active():
                self.ssh.command("mount -a")
                self.logger.info("reboot succeed")
                result = True
                break
            duration = time.time() - start_time
        return result

    def mcp(self, safe_pc=True):
        """This is the method to do mcp with control_serial"""
        if self.control_serial:
            self.checkSerialPortWindows()
        # add preDownloadCheck to get power module. etc.
        self.preDownloadCheck()
        time.sleep(5)
        self.do_uart_process_with_pc(process_name="mcp", max_wait_time=180)
        if safe_pc:
            self.safe_pc()
        if self.control_serial:
            self.openSerialWindows(log_path=os.path.join(projectRootPath, "log", "UART_LOG"))

    def tcg_provision(self, ser=None):
        self.logger.info("Provision drive by uart")
        self.sendUartCmd(ser=ser,
                         cmdStr=b"tcginit",
                         waitPattern=b"RFS read/write DONE",
                         timeout=30)
        self.sendUartCmd(ser=ser, cmdStr=b"ver", waitPattern=b"TCG OK To Create NS", timeout=10)

    def tcg_de_provision(self, ser=None):
        self.logger.info("De-Provision drive by uart")
        self.sendUartCmd(ser=ser,
                         cmdStr=b"tcgfini",
                         waitPattern=b"RFS read/write DONE",
                         timeout=30)
        self.do_uart_process_with_pc(process_name="mcp", max_wait_time=180, ser=ser)
        self.sendUartCmd(ser=ser, cmdStr=b"ver", waitPattern=b"TCG OK To Create NS", timeout=10)

    def check_tcg_status(self, ser=None):
        try:
            wait_pattern_exist, response_str = self.sendUartCmd(ser=ser,
                                                                cmdStr=b"ver",
                                                                waitPattern=b"TCG OK To Create NS",
                                                                timeout=10)
            if wait_pattern_exist:
                drive_sn_list = re.findall(b"Drive SN +: +[\w]{18}", response_str)
                drive_tcg_type_list = re.findall(b"Security type + : +[\w]{3}", response_str)
                drive_tcg_provision_list = re.findall(b"TCG Provisioned + : +[\w]{3}", response_str)
                if drive_sn_list:
                    drive_sn = drive_sn_list[0].split(b" ")[-1].decode("latin1", errors="replace")  # split(":")[-1]
                    drive_tcg_type = drive_tcg_type_list[0].split(b" ")[-1].decode("latin1", errors="replace")
                    drive_tcg_provision = drive_tcg_provision_list[0].split(b" ")[-1].decode("latin1", errors="replace")
                    self.logger.info(
                        "Dive SN: {}, drive tcg type: {}, drive provision status: {}".format(drive_sn, drive_tcg_type,
                                                                                             drive_tcg_provision))
                    if drive_tcg_provision == "Yes":
                        self.logger.info(
                            "Drive is provision, and drive tcg type: {}, tcg provision check pass!".format(
                                drive_tcg_type))
                    else:
                        self.logger.error("TCG provision check fail!!!!!")

            else:
                self.logger.warning("Get drive SN failed, skip this step")
        except Exception as e:
            self.logger.warning(e)

    def run(self, retryCount=1):
        self.print_event("Do pre download check 1")
        if self.control_serial:
            self.close_serial_port()
        else:
            self.isNeedOpenSerial = self.checkSerialPortWindows()
        self.preDownloadCheck()
        self.print_event("Start 2 step download process")
        dnld_success = False
        while retryCount:
            retryCount -= 1
            self.print_event("Do 2 step download process loop %d" % (3 - retryCount))
            driveStatus = self.powerCycleGetDriveStatus()
            # Drive status unknown
            if driveStatus == self.DRIVE_STATUS_UNKNOWN:
                driveStatus = self.forceEnterBlBfbk()
            # Drive in main firmware
            if driveStatus in [self.DRIVE_IN_MAIN_FW, self.DRIVE_IN_PANIC_MODE, self.DRIVE_IN_ASSERT_MODE]:
                self.print_event("driveStatus in [self.DRIVE_IN_MAIN_FW, self.DRIVE_IN_PANIC_MODE, self.DRIVE_IN_ASSERT_MODE]")
                ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE, timeout=5)
                self.logger.info("Retrieve FW version")
                try:
                    self.sendUartCmd(ser, b"ver")
                except Exception as _:
                    self.sendUartCmd(ser, b"ver")
                if self.dlfw_tried:
                    self.print_event("Try download with 'dl fw' command")
                    ser.close()
                    driveStatus = self.DRIVE_IN_NEW_FW
                    if self.downloadFwInFw():
                        driveStatus = self.DRIVE_IN_NEW_FW
                        self.print_event("Download with 'dl fw' completed")
                        self.powerCycleGetDriveStatus()
                    else:
                        driveStatus = self.powerCycleGetDriveStatus()
                        self.print_event("Download with 'dl fw' failed")
                else:
                    # Erase nor sector 0, 1, 16, 32, 33 (sectore size is 4KiB)
                    self.print_event("clearspi 1 before spier")
                    self.sendUartCmd(ser, b"clearspi 1", b"clearspi complete")
                    self.print_event("Erase NOR flash")
                    for page in [0, 1]:
                        self.sendUartCmd(ser, b"spier %d\n" % page)
                    self.print_event("Erase NOR flash done")
                    ser.close()
                    driveStatus = self.powerCycleGetDriveStatus()
            # Drive in bootloader (erase bootloader, next status is boot rom)
            if driveStatus == self.DRIVE_IN_BOOT_LOADER:
                self.print_event("driveStatus == self.DRIVE_IN_BOOT_LOADER")
                self.eraseBootloaderInBl()
                driveStatus = self.powerCycleGetDriveStatus()
            # Drive in boot rom (download spi app, next status in spi app)
            if driveStatus == self.DRIVE_IN_BOOT_ROM:
                self.print_event("driveStatus == self.DRIVE_IN_BOOT_ROM")
                self.print_event("Download SPI APP")
                self.logger.info("self.preDnldBin = {}".format(self.preDnldBin))
                self.logger.info("waitPattern = {}".format(download_main_fw_str))
                if not self.isDriveInUartDnld(self.ROM_BAUDRATE, nakInterval=5):
                    self.logger.info("Drive in BOOT ROM but not in UART download, retry")
                    continue
                self.xmodemSendFile(serialPort=self.serialPort, baudrate=self.ROM_BAUDRATE,
                                    filePath=self.preDnldBin, waitPattern=download_main_fw_str,
                                    maxWaitTime=15)
                time.sleep(1)
                self.print_event("Download SPI APP done")
            driveStatus = self.DRIVE_IN_SPI_APP
            # Drive in SPI app (download new FW, next status is new firmware)
            if driveStatus == self.DRIVE_IN_SPI_APP:
                self.print_event("driveStatus == self.DRIVE_IN_SPI_APP")
                self.print_event("Download firmware")
                self.logger.info("self.firmwarePath = {} ".format(self.firmwarePath))
                self.logger.info("waitPattern = Power Cycle........ ")
                if not self.isDriveInUartDnld(self.DNLD_BAUDRATE, nakInterval=5):
                    self.logger.info("After download SPI APP, not in UART download, retry")
                    continue
                self.xmodemSendFile(serialPort=self.serialPort, baudrate=self.DNLD_BAUDRATE,
                                    filePath=self.firmwarePath, waitPattern=b"Power Cycle........",
                                    maxWaitTime=self.MAX_FW_SAVE_TIME)
                driveStatus = self.powerCycleGetDriveStatus()
                if driveStatus in [self.DRIVE_IN_MAIN_FW, self.DRIVE_IN_PANIC_MODE, self.DRIVE_IN_ASSERT_MODE]:
                    if driveStatus in [self.DRIVE_IN_PANIC_MODE, self.DRIVE_IN_ASSERT_MODE]:
                        self.logger.info(
                            "Wait for sometime for case FW didn't complete dumping panic file (Reset + dump panic file).")
                        time.sleep(60)
                    self.print_event("Download firmware succeeded")
                    driveStatus = self.DRIVE_IN_NEW_FW
                else:
                    self.print_event("Download firmware failed")
                    continue
            # Drive in new firmware (Download LDPC table then erasespi 1, power cycle)
            if driveStatus == self.DRIVE_IN_NEW_FW:
                time.sleep(30)
                self.print_event("driveStatus == self.DRIVE_IN_NEW_FW,Verify downloaded FW version")
                uartFwVerStr = self.getFwCommitIdFromUart()
                if self.binFwVerStr and self.binFwVerStr != uartFwVerStr:
                    self.logger.error("Commit version incorrect, expect: %s, actual: %s" %
                                      (self.binFwVerStr, uartFwVerStr))
                    continue
                # If SPI command is used, MCP is not necessary as it is default triggered
                if self.mcp_required:
                    if not self.do_uart_process_with_pc(process_name="mcp", max_wait_time=300):
                        continue
                    else:
                        self.print_event("Check TCG status")
                        ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE)
                        self.check_tcg_status(ser=ser)
                        ser.close()
                        if not self.do_uart_process_with_pc(process_name="mcp", max_wait_time=300):
                            continue
                if self.oakgate:
                    self.print_event("Rescan drive slot ")
                    try:
                        oak_obj = get_oakgate(self.oakgate)
                        rescan_pcie_slot(oak_obj, logger=self.logger)
                    except Exception as e:
                        self.logger.error(e)
                        self.logger.info("Try to rescan device again")
                        try:
                            oak_obj = get_oakgate(self.oakgate)
                            rescan_pcie_slot(oak_obj, logger=self.logger)
                        except Exception as e:
                            self.logger.error(e)
                            self.logger.error("Rescan target device failed after PD and power cycle")
                            continue
                elif self.iroc:
                    self.exec_ssh_cmd("nvme list")
                    status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                    if 'No such file or directory' in cmd_ret:
                        dev_cnt = 0
                    else:
                        dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                        dev_cnt_list = set(dev_all_cnt)
                        dev_cnt = len(dev_cnt_list)
                    self.logger.info('find {} nvme device'.format(dev_cnt))
                    #if self.quarch_dev_str and "SERIAL:/dev/ttyUSB" in self.quarch_dev_str:
                    if self.quarch_dev_str:
                        quarch_poweron_str = "RUN:POWer UP"
                        quarch_poweroff_str = "RUN:POWer DOWN"
                        quarch_cmd_poweron_str = 'python -c "from quarchpy.device import * ; ' \
                                                 'from quarchpy.disk_test.driveTestCore import executeAndCheckCommand;' \
                                                 'temp= quarchDevice(\'{}\');' \
                                                 'executeAndCheckCommand(temp, \'{}\')"'.format(self.quarch_dev_str,
                                                                                                quarch_poweron_str)
                        quarch_cmd_poweroff_str = 'python -c "from quarchpy.device import * ; ' \
                                                  'from quarchpy.disk_test.driveTestCore import executeAndCheckCommand;' \
                                                  'temp= quarchDevice(\'{}\');' \
                                                  'executeAndCheckCommand(temp, \'{}\')"'.format(self.quarch_dev_str,
                                                                                                 quarch_poweroff_str)
                        self.powerOffHandle = lambda: self.exec_ssh_cmd(quarch_cmd_poweroff_str)
                        time.sleep(self.POWER_OFF_WAIT)
                        self.powerOnHandle = lambda: self.exec_ssh_cmd(quarch_cmd_poweron_str)
                        time.sleep(self.POWER_OFF_WAIT)
                        self.exec_ssh_cmd("nvme list")
                        status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                        if 'No such file or directory' in cmd_ret:
                            dev_cnt = 0
                        else:
                            dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                            dev_cnt_list = set(dev_all_cnt)
                            dev_cnt = len(dev_cnt_list)
                        self.logger.info('find {} nvme device'.format(dev_cnt))
                    elif self.cnextb_dev_str:
                        cnextb_poweron_str = "RUN:POWer UP"
                        cnextb_poweroff_str = "RUN:POWer DOWN"
                        cnextb_cmd_poweron_str = 'python -c "from cnextb.device import * ; ' \
                                                 'temp= CnextbDevice(\'{}\');' \
                                                 'executeAndCheckCommand(temp, \'{}\')"'.format(self.cnextb_dev_str,
                                                                                                cnextb_poweron_str)
                        cnextb_cmd_poweroff_str = 'python -c "from cnextb.device import * ; ' \
                                                  'temp= CnextbDevice(\'{}\');' \
                                                  'executeAndCheckCommand(temp, \'{}\')"'.format(self.cnextb_dev_str,
                                                                                                 cnextb_poweroff_str)
                        self.powerOffHandle = lambda: self.exec_ssh_cmd(cnextb_cmd_poweroff_str)
                        time.sleep(self.POWER_OFF_WAIT)
                        self.powerOnHandle = lambda: self.exec_ssh_cmd(cnextb_cmd_poweron_str)
                        time.sleep(self.POWER_OFF_WAIT)
                        self.exec_ssh_cmd("nvme list")
                        status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                        if 'No such file or directory' in cmd_ret:
                            dev_cnt = 0
                        else:
                            dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                            dev_cnt_list = set(dev_all_cnt)
                            dev_cnt = len(dev_cnt_list)
                        self.logger.info('find {} nvme device'.format(dev_cnt))
                    else:
                        self.reboot()
                        result = self.wait_reboot_complete()
                        self.logger.info("Reboot complete:{}".format(result))
                        time_out = 600
                        start_time = time.time()
                        current_time = start_time
                        duration = current_time - start_time
                        while duration < time_out:
                            time.sleep(30)
                            duration = time.time() - start_time
                            self.exec_ssh_cmd("nvme list")
                            status, cmd_ret = self.exec_ssh_cmd("ls /dev/nvme*")
                            if 'No such file or directory' in cmd_ret:
                                dev_cnt = 0
                            else:
                                dev_all_cnt = re.compile("nvme(.)").findall(cmd_ret)
                                dev_cnt_list = set(dev_all_cnt)
                                dev_cnt = len(dev_cnt_list)
                            self.logger.info('find {} nvme device'.format(dev_cnt))
                            if dev_cnt:
                                break
                            self.reboot()
                            result = self.wait_reboot_complete()
                            self.logger.info("Reboot complete:{}".format(result))
                dnld_success = True
                break

        if dnld_success:
            self.print_event("two step download succeeded")
        else:
            self.print_event("two step download failed")
            raise Exception("Two step download failed")

        self.print_event("Open teraterm after two step download")
        if self.control_serial:
            try:
                self.openSerialWindows(log_path=os.path.join(projectRootPath, "log", "UART_LOG"))
            except Exception as e:
                self.logger.warning(e)
        else:
            try:
                self.openSerialWindows(log_path=options.logPath)
            except Exception as e:
                self.logger.warning(e)
        self.print_event("The whole two step download is completed , and it's successful")

    def isDriveInFirmware(self):
        ser = serial.Serial(port=self.serialPort, baudrate=self.FW_BAUDRATE, timeout=1)
        ser.write(b"\n")
        time.sleep(4)
        responseStr = ser.read_until(self.FW_UART_RESP_SUFFIX_STR)
        self.logger.info(responseStr)
        ser.close()
        if self.FW_UART_RESP_SUFFIX_STR in responseStr:
            return True
        return False

    def isDriveInUartDnld(self, baudrate, nakInterval=5, ser=None):  # xmodem stand is 3s
        self.logger.info("enter in is DriveInUartDnld ")
        if not ser:
            ser = serial.Serial(port=self.serialPort, baudrate=baudrate, timeout=0.2)

        ser.flushInput()
        receiveStr = b""
        MAX_TIMEOUT = nakInterval * 3
        startTime = time.time()  # Wait an vaild xmodem char
        while time.time() - startTime < MAX_TIMEOUT:
            receiveStr += ser.read()
            if receiveStr[-2:] == xmodem.NAK * 2:
                break
        if not ser:
            ser.close()
        if receiveStr[-2:] == xmodem.NAK * 2:
            return True
        return False
        """
        @note: Current hard code support Oakgate, for varies platform, please update that
        """
        #  rootPath = os.getcwd() if 'Utility' not in os.getcwd() else os.path.split(os.getcwd())[0]
        #  deviceFilePath = os.path.join(rootPath, 'Config', 'BasicConfig', 'oakgate.yaml')
        deviceSum = get_oakgate(self.oakgate)
        #  with open(deviceFilePath, 'r') as deviceFile:
        #  yamlStr = deviceFile.read()
        #  try:
        #  deviceSumDict = yaml.load(yamlStr, yaml.FullLoader)
        #  except Exception as _:
        #  deviceSumDict = yaml.load(yamlStr)
        #  deviceSum = deviceSumDict[arguments]
        # Check if SVF client not running
        if os.name == "nt":
            _, restPort = self.checkEnvironmentWindows()
        else:
            raise EnvironmentError("Can't support OS type %s, please fix that" % os.name)
        restClient = RestClient("127.0.0.1:%d" % restPort)
        # Connect to remote Oakgate system
        WAIT_TIME = 60
        startTime = time.time()
        isNeedScan = True
        self.logger.info("Scan for target server: {}".format(deviceSum["sys_name"]))
        while True:
            discoverySystems = restClient.finder.get_discovery_system_collection()
            discoverySystem = None
            for discoverySystem in discoverySystems:
                if discoverySystem.name.upper() == deviceSum["sys_name"]:
                    # Workaround for system not have chassis, ensure system have chassis
                    discoveryChassis = restClient.finder.get_discovery_chassis_collection(discoverySystem.uid)
                    if discoveryChassis:
                        break
                    else:
                        discoverySystem = None
                        isNeedScan = True
                else:
                    discoverySystem = None
            if discoverySystem is not None:
                break
            elif time.time() - startTime > WAIT_TIME:
                raise EnvironmentError(
                    "Can't find target server:%s, please check you server name or network" % deviceSum["sys_name"])
            elif isNeedScan:
                restClient.finder.set_subnets(deviceSum["sub_net"])
                restClient.finder.scan_subnets()
                isNeedScan = False
            time.sleep(0.5)
        # Check if port is running, if running stop that
        WAIT_TIME = 60
        discoveryChassis = restClient.finder.get_discovery_chassis_collection(discoverySystem.uid)
        self.logger.info("Stop target server: {}".format(deviceSum["sys_name"]))
        for chassis in discoveryChassis:
            if chassis.state == DiscoState.DRIVER_STATE_STOPPED:
                continue
            discoverySlots = restClient.finder.get_discovery_slot_collection(chassis.uid)
            for slot in discoverySlots:
                device_collection = restClient.finder.get_discovery_device_collection(slot.uid)
                for device in device_collection:
                    #  self.logger.info(device.device_bdf_string)
                    if deviceSum["slot_num"] == device.device_bdf_string:
                        self.logger.info("Discovered physical slot number:{}".format(slot.slot_number))
                        self.logger.info("Discovered slot PCI bus number:{}".format(slot.pci_bus_number))
                        self.logger.info("Discovered drive:{}".format(device.device_bdf_string))

                        startTime = time.time()
                        while device.state != DiscoState.DRIVER_STATE_STOPPED:
                            if time.time() - startTime > WAIT_TIME:
                                raise EnvironmentError(
                                    "Can't stop device in %d seconds, drive status is %s" %
                                    (WAIT_TIME, device.state))
                            lockOwnersUser = [lockOwner.user for lockOwner in device.lock_owners]
                            # Use slot operation for dual port
                            if deviceSum["username"] not in lockOwnersUser:
                                restClient.finder.force_unlock_discovery_slot(slot.uid)
                            if device.state != DiscoState.DRIVER_STATE_STOPPING:
                                restClient.finder.stop_discovery_slot(slot.uid, deviceSum["username"])
                            time.sleep(1)
                            device = restClient.finder.get_discovery_device(device.uid)
                        self.logger.info("Target device %s stop success" % device.device_bdf_string)
                        break

        # Connect Oakgate power module
        PC_TYPE_LIST = ["QuarchIp", "Magma", "Ippc", "RelayIp", "TanisysIp", "OakgateInterposerIp",
                        "CheetahIp", "MezzanineIp"]
        peripheralIp = discoverySystem.remote_ip_address
        if deviceSum["pwr_type"] not in PC_TYPE_LIST:
            raise EnvironmentError(
                "Unknown power controller type %s, please refer %s" % (deviceSum["pwr_type"], PC_TYPE_LIST))
        WAIT_TIME = 1240
        needDoConnect = True
        startTime = time.time()
        self.logger.info("Connect to power module of target server: {}".format(deviceSum["sys_name"]))

        def connect_power_module(power_type, sys_ip, sys_uid):
            self.logger.info("PwrType: %s, IP: %s, UID: %s" % (power_type, sys_ip, sys_uid))
            keyValueSet = KeyBuilder()
            try:
                keyValueSet.addKeyVal(".ipAddress", "")
                restClient.peripheral.connect_to_peripheral_connection(
                    sys_ip, sys_uid, power_type, keyValueSet)
            except Exception as _:
                keyValueSet.addKeyVal(".ipAddress", sys_ip)
                restClient.peripheral.connect_to_peripheral_connection(
                    sys_ip, sys_uid, power_type, keyValueSet)
            self.logger.info("Power module connected")

        while True:
            connections = restClient.peripheral.get_peripheral_connection_collection()
            connection = None
            for connection in connections:
                if connection.type_id == deviceSum["pwr_type"] and connection.ip_address == peripheralIp:
                    break
                else:
                    connection = None
            if connection is not None:
                break
            if needDoConnect:
                try:
                    connect_power_module(deviceSum["pwr_type"], peripheralIp, discoverySystem.uid)
                except Exception as e:
                    # TODO: remove this retry after SVF issue fixed
                    self.logger.info("Failed to connect to power module, reboot system and retry")
                    self.logger.info(e)
                    if self.allow_reboot:
                        discoverySystem = reboot_oak_sys(deviceSum, logger=self.logger)
                    time.sleep(30)
                    connect_power_module(deviceSum["pwr_type"], peripheralIp, discoverySystem.uid)
                needDoConnect = False
            if time.time() - startTime > WAIT_TIME:
                raise EnvironmentError(
                    "After wait %s seconds can't connect to power controller, please check your parameter setup" % WAIT_TIME)
            time.sleep(0.5)
        # Get power module
        restClient.peripheral.wait_timeout = 2
        restClient.peripheral.max_retries = 2
        wait_time = 10
        try:
            controllers = restClient.peripheral.get_peripheral_controller_collection(connection.uid)
            controller = controllers[deviceSum["ctrl_id"]]
            modules = restClient.peripheral.get_peripheral_module_collection(controller.uid)
            powerModule = modules[deviceSum["module_id"]]
            currentPowerStatus = restClient.peripheral.get_power_on(powerModule.uid)
            originalWaitTimeout = restClient.peripheral.wait_timeout
            originalMaxRetries = restClient.peripheral.max_retries
            expected_state = not currentPowerStatus
            self.set_power_state(restClient, deviceSum, powerModule, expected_state)

            if expected_state == False:
                expected_state = True
                self.set_power_state(restClient, deviceSum, powerModule, expected_state)

            self.logger.info("Sleep {} seconds after power {}.".format(wait_time, expected_state))
            time.sleep(wait_time)
            restClient.peripheral.wait_timeout = originalWaitTimeout
            restClient.peripheral.max_retries = originalMaxRetries
        except Exception as e:
            self.logger.info(e)
            self.logger.info("Power module connection lost, reconnect in %d secs" % originalWaitTimeout)
            try:
                restClient.peripheral.wait_timeout = originalWaitTimeout
                restClient.peripheral.max_retries = originalMaxRetries
                restClient.peripheral.disconnect_to_peripheral_connection(connection.uid)
                restClient.finder.restart_power_software(discoverySystem.uid, deviceSum["username"])
                connect_power_module(deviceSum["pwr_type"], peripheralIp, discoverySystem.uid)
            except Exception as e:
                # TODO: remove this retry after SVF issue fixed
                self.logger.info("Failed to connect to power module, reboot system and retry")
                self.logger.info(e)
                if self.allow_reboot:
                    discoverySystem = reboot_oak_sys(deviceSum, logger=self.logger)
                connect_power_module(deviceSum["pwr_type"], peripheralIp, discoverySystem.uid)
            while True:
                connections = restClient.peripheral.get_peripheral_connection_collection()
                connection = None
                for connection in connections:
                    if connection.type_id == deviceSum["pwr_type"] and connection.ip_address == peripheralIp:
                        break
                    else:
                        connection = None
                if connection is not None:
                    break
                if time.time() - startTime > WAIT_TIME:
                    raise EnvironmentError("After wait %s seconds reconnect to power controller" % WAIT_TIME)
                time.sleep(0.5)
            controllers = restClient.peripheral.get_peripheral_controller_collection(connection.uid)
            assert len(controllers) == 1
            controller = controllers[0]
            modules = restClient.peripheral.get_peripheral_module_collection(controller.uid)
            powerModule = modules[deviceSum["module_id"]]
            currentPowerStatus = restClient.peripheral.get_power_on(powerModule.uid)
        self.powerOnHandle = lambda: restClient.peripheral.set_power_on(powerModule.uid, True)
        self.powerOffHandle = lambda: restClient.peripheral.set_power_on(powerModule.uid, False)
        self.powerOffHandle()
        rescan_pcie_slot(deviceSum, logger=self.logger)

    def checkEnvironmentWindows(self):

        def init_ctrl_path():
            """
            Init oakgate controller path(svf software)
            :return:
            """

            def _compare_ver(ver1, ver2):
                lena = len(ver1.split('.'))
                lenb = len(ver2.split('.'))
                a2 = ver1 + '.0' * (lenb-lena)
                b2 = ver2 + '.0' * (lena-lenb)
                for i in range(max(lena, lenb)):
                    if int(a2.split('.')[i]) > int(b2.split('.')[i]):
                        return ver1
                    elif int(a2.split('.')[i]) < int(b2.split('.')[i]):
                        return ver2
                    else:
                        if i == max(lena, lenb)-1:
                            return ver1

            controller_path = None
            latest_oakgate_ver = '0.0'

            pc_user_name = getpass.getuser()
            user_path_list = os.listdir(r"C:\Users")
            if pc_user_name in user_path_list:
                pc_user_path_name = pc_user_name
            elif pc_user_name in str(user_path_list):
                pc_user_path_name = [path_temp for path_temp in user_path_list if pc_user_name in path_temp][0]
            else:
                pc_user_path_name = "Administrator"
            oakgate_root_path_list = [r"C:\Users\{}\OakGate".format(pc_user_path_name), r"C:\Program Files (x86)\OakGate", r"C:\Program Files\OakGate"]
            for oakgate_absolute_path in oakgate_root_path_list:
                if os.path.isdir(oakgate_absolute_path):

                    oakagte_version_list = [re.split('[-_]', path_temp)[1][1:] for path_temp in os.listdir(oakgate_absolute_path)]
                    for version in oakagte_version_list:
                        latest_oakgate_ver = _compare_ver(latest_oakgate_ver, version)

                    latest_oakgate_version_num = max([path_temp for path_temp in os.listdir(oakgate_absolute_path) if latest_oakgate_ver in path_temp])
                    controller_path = os.path.join(oakgate_absolute_path, latest_oakgate_version_num, "ApplicationUIBundle")

                    print("Oakgate controller path: {}".format(controller_path))
                    break
            if not controller_path:
                raise Exception("SVF path is not exist, please start SVF manually")

            return controller_path

        def start_svf(controller_path):
            startDir = os.getcwd()
            if os.path.isdir(controller_path):
                pass
            else:
                raise Exception("SVF path is not exist")
            os.chdir(os.path.join(controller_path, 'bin'))
            bat_path = os.path.join(controller_path, 'bin', 'call_oakgate.bat')
            if os.path.exists(bat_path):
                pass
            else:
                self.logger.info("create")
                with open(bat_path, 'w+') as f:
                    f.write('start ApplicationUIBundle.bat')
            os.system("call call_oakgate.bat")
            os.chdir(startDir)

        controller_path = init_ctrl_path()
        cliPort, restPort = self._getSvfServicePortsWindows()
        if not cliPort or not restPort:
            start_svf(controller_path)

            WAIT_TIME = 30
            startTime = time.time()
            while cliPort is None or restPort is None:
                time.sleep(1)
                if time.time() - startTime > WAIT_TIME:
                    raise EnvironmentError("Can't start SVF controller service in %d seconds" % WAIT_TIME)
                cliPort, restPort = self._getSvfServicePortsWindows()
        return cliPort, restPort

    def _getSvfServicePortsWindows(self):
        CLI_SERVER_PORT_LIST = [7779, 7879, 7979, 8079, 8179, 8279, 8379, 8749, 8579, 8679]
        REST_SERVER_PORT_LIST = [9998, 9999, 10000, 10001, 10002, 10003, 10004, 10005, 10006, 10007]
        chkPsCmdStr = "tasklist.exe -V -FI \"IMAGENAME EQ java.exe\""
        cmdRun = subprocess.Popen(args=chkPsCmdStr, stdout=subprocess.PIPE)
        outputLines = cmdRun.stdout.readlines()
        # outputLines = [line for line in outputLines if "OakGate Technology Validation Framework" in line]
        outputLines = [line for line in outputLines if b"OakGate Enduro powered by SVF Pro" in line]
        if not outputLines:
            return None, None
        else:
            pid = outputLines[0].strip().split()[1]
        chkPortCmdStr = "netstat -ano -p TCP"
        cmdRun = subprocess.Popen(args=chkPortCmdStr, stdout=subprocess.PIPE)
        outputLines = cmdRun.stdout.readlines()
        listeningList = [line.strip().split() for line in outputLines if b"LISTENING" in line]
        portList = [int(localAddr.split(b":")[-1]) for _, localAddr, _, _, portPid in listeningList if portPid == pid]
        cliPortList = [port for port in portList if port in CLI_SERVER_PORT_LIST]
        restPortList = [port for port in portList if port in REST_SERVER_PORT_LIST]
        if not cliPortList:
            cliPort = None
        elif len(cliPortList) == 1:
            cliPort = cliPortList[0]
        else:
            raise EnvironmentError("cliPortList have multi port, please check that %s" % cliPortList)
        if not restPortList:
            restPort = None
        elif len(restPortList) == 1:
            restPort = restPortList[0]
        else:
            raise EnvironmentError("restPortList have multi port, please check that %s" % restPortList)
        return cliPort, restPort

    def safe_pc_iroc(self):
        def reboot_iroc():
            self.exec_ssh_cmd("sudo -S reboot")
            time.sleep(1)
            for i in range(10):
                try:
                    self.exec_ssh_cmd("echo success")
                    break
                except Exception as _:
                    self.logger.info("Sleep 30 seconds to wait for iROC OS back")
                    time.sleep(30)
            else:
                raise Exception("Can not connect to iroc after 5min")

        self.print_event("Reboot iroc system before safe power cycle")
        reboot_iroc()
        self.do_uart_process_with_pc(process_name="clean_pc", max_wait_time=180)
        self.print_event("Reboot iroc system after safe power cycle")
        reboot_iroc()
        time.sleep(1)
        #  self.restart_drive_iroc()

    def safe_pc_oakgate(self):
        oak_obj = get_oakgate(self.oakgate)
        rescan_pcie_slot(oak_obj, logger=self.logger)
        self.print_event("Initialize SSD")
        dev = init_device(oak_obj)
        dev.safe_power_cycle()
        # TODO: remove rescan after safe power cycle with rescan ready
        rescan_pcie_slot(oak_obj, logger=self.logger)

    def safe_pc(self):
        if self.iroc:
            self.safe_pc_iroc()
            return
        if self.oakgate:
            self.safe_pc_oakgate()
            return

    def set_power_state(self, restClient, deviceSum, powerModule, expected_state):
        wait_time = 10
        for retry in range(3):
            self.logger.info("Set Power {} on SSD to {} for the {} time"
                             .format(deviceSum["sys_name"], expected_state, retry))
            restClient.peripheral.set_power_on(powerModule.uid, expected_state)
            self.logger.info("Wait up to {}s to power {}".format(wait_time, expected_state))
            cur_power_state = restClient.peripheral.get_power_on(powerModule.uid)
            if cur_power_state != expected_state:
                time_start = time.time()
                while time.time() - time_start < wait_time:
                    time.sleep(1)
                    cur_power_state = restClient.peripheral.get_power_on(powerModule.uid)
                    if cur_power_state == expected_state:
                        break
            if cur_power_state == expected_state:
                break
        else:
            raise Exception(
                "Set Power {} on SSD to {} fail".format(deviceSum["sys_name"], expected_state))

def checkOakgateName(oakgateName):
    rootPath = os.getcwd() if 'Utility' not in os.getcwd() else os.path.split(os.getcwd())[0]
    deviceFilePath = os.path.join(rootPath, 'Config', 'BasicConfig', 'oakgate.yaml')
    with open(deviceFilePath, 'r') as deviceFile:
        yamlStr = deviceFile.read()
        try:
            deviceSumDict = yaml.load(yamlStr, yaml.FullLoader)
        except Exception as _:
            deviceSumDict = yaml.load(yamlStr)
    oakgateList = list(deviceSumDict.keys())
    if oakgateName not in oakgateList:
        raise ValueError("Unknow oakgate Name %s, please use below list:\n%s" % (oakgateName, oakgateList))
    return oakgateName

def init_device(oak_obj):
    client = RestClient(oak_obj['ip_addr'] + ":9998")
    #  client.finder.set_subnets(oak_obj['sub_net'])
    #  client.finder.scan_subnets()
    dev = Device(rest_port="9998",
                 platform="oakgate",
                 hardware="Redtail",
                 project="Redtail",
                 **oak_obj
                 )

    dev.init_device()
    return dev

def rescan_pcie_slot(oak_obj, logger):
    """Rescan PCIe slot"""
    client = RestClient(oak_obj['ip_addr'] + ":9998")
    subnets = oak_obj['sub_net']
    disco_system = None
    system_uid = None
    system_name = oak_obj['sys_name']
    found = False
    scan_num = 2
    while scan_num >= 0 and found is False:
        logger.info("Scan {} loop {}".format(oak_obj["slot_num"], 3 - scan_num))
        scan_num -= 1
        try:
            client.finder.set_subnets(subnets)
            client.finder.scan_subnets()
        except Exception as _:
            time.sleep(1)
            client.finder.set_subnets(subnets)
            client.finder.scan_subnets()

        for system in client.finder.get_discovery_system_collection():
            if system.name == system_name:
                disco_system = system
                system_uid = system.uid
                logger.info("Found {}".format(system_name))
                break

        if disco_system is None:
            continue

        # Scan all stopped slots, TODO: add targeted scan
        chassis_list = client.finder.get_discovery_chassis_collection(system_uid)
        slot_collection = []
        for single_chassis in chassis_list:
            slot_collection.extend(client.finder.get_discovery_slot_collection(single_chassis.uid))
        for single_slot in slot_collection:
            if single_slot.state in [DiscoState.DRIVER_STATE_STOPPED,
                                     # Below status is true after upgrade power driver
                                     DiscoState.DRIVER_STATE_UPDATED,
                                     DiscoState.DRIVER_STATE_EMPTY_SLOT]:
                client.finder.rescan_discovery_slot(single_slot.uid)
        time.sleep(5)

        for single_slot in slot_collection:
            if found:
                break
            dev_list = client.finder.get_discovery_device_collection(single_slot.uid)
            for device in dev_list:
                if oak_obj["slot_num"] != device.device_bdf_string:
                    continue
                #  if single_slot.state == DiscoState.DRIVER_STATE_STOPPED:
                if single_slot.state in [DiscoState.DRIVER_STATE_STOPPED, DiscoState.DRIVER_STATE_EMPTY_SLOT]:
                    logger.info("Rescan stopped slot %s " % oak_obj["slot_num"])
                    client.finder.rescan_discovery_slot(single_slot.uid)
                    found = True
                    break

                # Unlock whole slot as rescan/scan is slot based instead of device based
                logger.info("Force unlock started slot %s" % oak_obj["slot_num"])
                #  client.finder.unlock_discovery_slot(single_slot.uid, oak_obj["username"])
                try:
                    client.finder.force_unlock_discovery_slot(single_slot.uid)
                except Exception as _:
                    time.sleep(5)
                    client.finder.force_unlock_discovery_slot(single_slot.uid)
                start_time = time.time()
                while time.time() - start_time < 60:
                    time.sleep(2)
                    device = client.finder.get_discovery_device(device.uid)
                    if device.state != DiscoState.DRIVER_STATE_STOPPED:
                        continue
                    logger.info("Rescan stopped slot %s " % oak_obj["slot_num"])
                    client.finder.rescan_discovery_slot(single_slot.uid)
                    found = True
                    break
                else:
                    raise Exception("Drive isn't stopped in 60sec, status: %s" % device.state)
                break

    if disco_system is None:
        raise Exception("Failed to find system {0}".format(system_name))

    if not found:
        logger.error("Can't found device %s" % oak_obj["slot_num"])
    else:
        time.sleep(25)


if __name__ == "__main__":
    optparser = OptionParser()
    optparser.add_option("--oakgate", default=None, help="Target drive location")
    optparser.add_option("--iroc", default=None,
                         help="The iroc info, format 'ip:drivenumber' or 'ip:drivenumber:pcpport'")
    optparser.add_option("--serialPort", default=None, help="Serial port, Example: COM3")
    optparser.add_option("--preBinPath", default=None, help="Predownload binary file path")
    optparser.add_option("--firmwarePath", default=None, help="product firmware binary path(cap)")
    optparser.add_option("--firmwarePathBin", default=None, help="product firmware binary path")
    optparser.add_option("--control_serial", default=False, action='store_true',
                         help="Flag to indicate if close/open serial")
    optparser.add_option("--loggerLevel", default="INFO", help="Set up logger level, debug for debug")
    optparser.add_option("--logPath", default=None, help="Set up logger level, debug for debug")
    optparser.add_option("--allow_reboot", default=False, action='store_true',
                         help="Flag to allow 2step process reboot host")
    optparser.add_option("--dlfw_tried", default=False, action='store_true',
                         help="Flag to decide whether try DL FW")
    (options, args) = optparser.parse_args()
    if not os.path.exists(options.preBinPath):
        raise ValueError("Unknown pre download path %s" % options.preBinPath)
    if not os.path.exists(options.firmwarePath):
        raise ValueError("Unknown firmware binary path %s" % options.firmwarePath)
    if options.oakgate:
        drive_name = options.oakgate
    elif options.iroc:
        drive_name = options.iroc
    logger = create_logger(drive_name).get_log()
    if options.oakgate is not None:
        oak_obj = get_oakgate(options.oakgate)
        if options.serialPort is None:
            options.serialPort = oak_obj.get('serial_port')
        twoStepDnld = TwoStepDownload(oakgate=checkOakgateName(options.oakgate),
                                      iroc=None,
                                      serialPort=options.serialPort,
                                      preBinPath=options.preBinPath,
                                      firmwarePath=options.firmwarePath,
                                      firmwarePathBin=options.firmwarePathBin,
                                      control_serial=options.control_serial,
                                      logger=logger,
                                      allow_reboot=options.allow_reboot,
                                      dlfw_tried=options.dlfw_tried)
    elif options.iroc:
        platform = 'iroc'
        twoStepDnld = TwoStepDownload(oakgate=None,
                                      iroc=options.iroc,
                                      serialPort=options.serialPort,
                                      preBinPath=options.preBinPath,
                                      firmwarePath=options.firmwarePath,
                                      firmwarePathBin=options.firmwarePathBin,
                                      control_serial=options.control_serial,
                                      logger=logger,
                                      allow_reboot=options.allow_reboot,
                                      dlfw_tried=options.dlfw_tried)
    twoStepDnld.run()
