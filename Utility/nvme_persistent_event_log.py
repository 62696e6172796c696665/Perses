import argparse
import sys
import os
import logging
from ctypes import byref, cast, POINTER, sizeof, c_uint64


sys.path.append("....")
sys.path.append("...")
sys.path.append("..")
sys.path.append(".")
currentPath = os.path.split(os.path.realpath(__file__))[0]
projectRootPath = os.path.abspath(os.path.join(currentPath, '..'))
utilPath = os.path.join(projectRootPath, 'util')
sys.path.append(projectRootPath)
sys.path.append(utilPath)


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger()
LOG.debug('__init__')

from lib.driver.nvme import Tahoe
from lib.driver.utils.ctype import Ctype
from lib.driver.nvme.struct.log_page import PersistentEventLog, PersistentEventEntry
from lib.driver.nvme.struct import persistent_event


help_action = """
    --- action the controller shall take
    during processing this
    persistent log page command.

"""

if __name__ == "__main__":
    nvme_persistent_event_types = {
        0x01: persistent_event.SmartHealthLogSnapshotEvent,
        0x02: persistent_event.NvmeFwCommitEvent,
        0x03: persistent_event.NvmeTimestampChangeEvent,
        0x04: persistent_event.NvmePowerOnResetInfoList,
        0x05: persistent_event.NvmeNssHwErrEvent,
        0x06: persistent_event.NvmeChangeNsEvent,
        0x07: persistent_event.NvmeFormatNvmStartEvent,
        0x08: persistent_event.NvmeFormatNvmComplnEvent,
        0x09: persistent_event.NvmeSanitizeStartEvent,
        0x0a: persistent_event.NvmeSanitizeComplnEvent,
        0x0b: persistent_event.NvmeSetFeatureEvent,
        0x0c: persistent_event.NvmePelTelementryCrt,
        0x0d: persistent_event.NvmeThermalExcEvent,
    }
    parser = argparse.ArgumentParser(
        description='nvme driver set streams for io')
    parser.add_argument('--block_device', '-d', type=str, default="/dev/nvme0n1", required=True, help='<device>')
    parser.add_argument('--action', "-a", default=0, required=True, type=int, help=help_action)
    args = parser.parse_args()
    nvme = Tahoe(block=args.block_device)
    if args.action != 0:
        status = nvme.get_log_persistent_log(action=args.action)
        sys.exit(status)
    else:
        pevent_log_info = nvme.get_log_persistent_log(action=0)
        if isinstance(pevent_log_info, int):
            LOG.info("status: %#x", pevent_log_info)
            sys.exit(pevent_log_info)
        persistent_event_log = cast(pevent_log_info.buf, POINTER(PersistentEventLog)).contents
        Ctype(persistent_event_log).dump()
        offset = sizeof(persistent_event_log)
        for _ in range(persistent_event_log.tnev):
            address = byref(pevent_log_info.buf, offset)
            pevent_entry_head = cast(address, POINTER(PersistentEventEntry)).contents
            Ctype(pevent_entry_head).dump()
            offset += pevent_entry_head.ehl + 3
            address = byref(pevent_log_info.buf, offset + pevent_entry_head.vsil)
            struct = nvme_persistent_event_types[pevent_entry_head.etype]
            if pevent_entry_head.etype == 0x04:
                por_event = struct()
                por_info_len = pevent_entry_head.el - pevent_entry_head.vsil - 8
                por_info_list = por_info_len // sizeof(por_event)
                fw_rev = cast(address, POINTER(c_uint64)).contents
                LOG.info(f"Firmware Revision: {fw_rev.value}")
                for i in range(por_info_list):
                    por_event = cast(byref(pevent_log_info.buf, offset + sizeof(fw_rev) + i * sizeof(por_event)),
                                     POINTER(persistent_event.NvmePowerOnResetInfoList)).contents
                    Ctype(por_event).dump()
            elif pevent_entry_head.etype == 0x0b:
                set_feat_event = cast(byref(pevent_log_info.buf, offset),
                                      POINTER(persistent_event.NvmeSetFeatureEvent)).contents
                fid = set_feat_event.cdw_mem[0] & 0x00ff
                cdw11 = set_feat_event.cdw_mem[1]
                LOG.info("\n|Set Feature ID\t|value\t\t|\n|%#02x\t\t|%#08x\t|", fid, cdw11)
            else:
                event_entry = cast(address, POINTER(struct)).contents
                Ctype(event_entry).dump()
            offset += pevent_entry_head.el
    