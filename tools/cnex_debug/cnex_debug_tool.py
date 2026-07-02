import fcntl
import os
from ctypes import *


class NVMePassthruCmd(Union):
    """
    Take Care: different with SQE!
    cdw8 is metadata_len and cdw9 is data_len
    Add cdw16: timeout
    Add cdw17: dword0 of CQE
    """

    class Bits(Structure):
        _pack_ = 1
        _fields_ = [
            ('opcode', c_uint8),
            ('flags', c_uint8),
            ('rsvd', c_uint16),
            ('nsid', c_uint32),
            ('cdw2', c_uint32),
            ('cdw3', c_uint32),
            ('meta', c_uint64),
            ('data', c_uint64),
            ('meta_len', c_uint32),
            ('data_len', c_uint32),
            ('cdw10', c_uint32),
            ('cdw11', c_uint32),
            ('cdw12', c_uint32),
            ('cdw13', c_uint32),
            ('cdw14', c_uint32),
            ('cdw15', c_uint32),
            ('timeout', c_uint32),
            ('result', c_uint32),
        ]

    class Cdws(Structure):
        _pack_ = 1
        _fields_ = [
            ('cdw', c_uint32 * 18),
        ]

    _anonymous_ = ('cdws', 'bits')
    _fields_ = [
        ('cdws', Cdws),
        ('bits', Bits),
    ]

def _iowr(_tp, _nr, _sz):
    return (3 << 30) + (sizeof(_sz) << 16) + (ord(_tp) << 8) + _nr

def _iow(_tp, _nr, _sz):
    return (1 << 30) + (sizeof(_sz) << 16) + (ord(_tp) << 8) + _nr

def _io(_tp, _nr):
    return (ord(_tp) << 8) + _nr

class NVMe:
    NVME_IOCTL_ADMIN_CMD = _iowr('N', 0x41, NVMePassthruCmd)
    NVME_IOCTL_IO_CMD = _iowr('N', 0x43, NVMePassthruCmd)

    def __init__(self, device='/dev/nvme', cntid=0, nsid=1, logfile=None):
        self._status = 0
        self._c_fd = -1
        self._b_fd = -1

        self._c_dev = "{}{}".format(device, cntid)
        self._b_dev = "{}{}n{}".format(device, cntid, nsid)

        if not logfile:
            self.fd = open(r'./cnex_dump.log', 'w')
        else:
            self.fd = open(logfile, 'w')

    def __del__(self):
        self._close_c_fd()
        self._close_b_fd()
        self.fd.close()

    @staticmethod
    def _open(dev):
        assert os.path.exists(dev), 'Device({}) is not exists'.format(dev)
        return os.open(dev, os.O_RDWR)

    @property
    def char_fd(self):
        if self._c_fd == -1:
            self._c_fd = self._open(self._c_dev)
        return self._c_fd

    @property
    def block_fd(self):
        if self._b_fd == -1:
            self._b_fd = self._open(self._b_dev)
        return self._b_fd

    def _close_c_fd(self):
        if self._c_fd != -1:
            os.close(self._c_fd)
            self._c_fd = -1

    def _close_b_fd(self):
        if self._b_fd != -1:
            os.close(self._b_fd)
            self._b_fd = -1

    def close(self):
        self.__del__()

    @staticmethod
    def _ioctl(fd, request, cmd=None, status=0):
        _status = fcntl.ioctl(fd, request, cmd) if cmd else fcntl.ioctl(fd, request)

        try:
            assert (_status & 0x7ff) == status, "CQE Status Field Check Failed!"
        except AssertionError:
            print('Actual Status: {:#x}, {}'.format(_status, STATUS_FIELD.get(_status & 0x7ff, 'Unknown')))
            print("Expect Status: {:#x}, {}".format(status, STATUS_FIELD.get(status & 0x7ff, 'Unknown')))
            if cmd:
                cmd_set = Opcode.ADMIN if isinstance(cmd, NVMePassthruCmd) else Opcode.IO
                print('Command : {}'.format(cmd_set.get(cmd.opcode, 'Unknown')))
                sqe = [(f[0], '{:#x}'.format(getattr(cmd.bits, f[0]))) for f in getattr(cmd.bits, '_fields_')]
                print('SQE : {}'.format(dict(sqe)))
            raise

        return _status

    def nvme_io(self, cmd, **kwargs):
        return self._ioctl(self.block_fd, self.NVME_IOCTL_SUBMIT_IO, cmd, **kwargs)

    def io_passthru(self, cmd, **kwargs):
        return self._ioctl(self.char_fd, self.NVME_IOCTL_IO_CMD, cmd, **kwargs)

    def admin_passthru(self, cmd, **kwargs):
        return self._ioctl(self.char_fd, self.NVME_IOCTL_ADMIN_CMD, cmd, **kwargs)

    def get_memory(self, addr, length=1, cpu=0):
        print("--------------Read Mem[addr:0x{:x}, length:{}]-----------".format(addr, length))
        dptr = (c_uint32 * length)()
        cmd = NVMePassthruCmd()
        cmd.opcode = 0xC0
        cmd.cdw10 = 0x10002005
        cmd.cdw11 = length
        cmd.cdw12 = cpu
        cmd.cdw13 = addr
        cmd.cdw14 = length * 4
        cmd.data = addressof(dptr)
        cmd.data_len = sizeof(dptr)
        self.admin_passthru(cmd)
        #print(sizeof(dptr))
        self.dump(self.fd, dptr, addr, length)
        return dptr

    @staticmethod
    def dump(fd, ptr, addr, length):
        data = cast(ptr, POINTER(c_uint32))
        #print(sizeof(data))
        for i in range(0, length, 4):
            line = ("Addr: 0x{:x}, data: {:08x} {:08x} {:08x} {:08x}\n".format(addr+4*i, data[i],data[i+1], data[i+2], data[i+3]))
            fd.write(line)



if __name__ == '__main__':
    dev = NVMe(cntid=0, nsid=1)
    # NTX
    dev.get_memory(0x14c004, length=1)
    dev.get_memory(0x146108, length=2)
    dev.get_memory(0x146120, length=2)
    dev.get_memory(0x146100, length=12)
    dev.get_memory(0x146000, length=50)
    # RDM
    dev.get_memory(0x192198, length=11)
    # DQD0
    dev.get_memory(0x1c4000, length=64)
    dev.get_memory(0x1c4100, length=64)
    # DQD1
    dev.get_memory(0x1c5000, length=64)
    dev.get_memory(0x1c5100, length=64)
    # DQD2
    dev.get_memory(0x1c6000, length=64)
    dev.get_memory(0x1c6100, length=64)
    # DQD3
    dev.get_memory(0x1c7000, length=64)
    dev.get_memory(0x1c7100, length=64)
    # FTL
    dev.get_memory(0x14ac00, length=4)
    dev.get_memory(0x14ac20, length=1)
    dev.get_memory(0x14ac7c, length=1)
    # PAP
    dev.get_memory(0x12a0d8, length=1)
    dev.get_memory(0x12a0e8, length=1)
    dev.get_memory(0x12a118, length=1)
    dev.get_memory(0x12a148, length=1)
    dev.get_memory(0x12a120, length=1)
    dev.get_memory(0x12a130, length=1)
    dev.get_memory(0x12a17c, length=1)
    # NRX
    dev.get_memory(0x14c000, length=14)
    # PCIE
    # DDA
    dev.get_memory(0x14102c, length=10)
    # NVC
    dev.get_memory(0x10c0e4, length=12)
    dev.get_memory(0x10c0b0, length=1)
    dev.get_memory(0x10c0b8, length=1)
    dev.get_memory(0x108058, length=48)
    dev.get_memory(0x108800, length=81)
    dev.get_memory(0x1050c0, length=145)
    dev.get_memory(0x105800, length=153)
    dev.get_memory(0x106840, length=51)
    dev.get_memory(0x107840, length=4)
    dev.get_memory(0x107850, length=4)
    dev.get_memory(0x107860, length=1)
    dev.get_memory(0x107890, length=4)
    dev.get_memory(0x1078a0, length=4)
    dev.get_memory(0x107880, length=3)
    dev.get_memory(0x107864, length=5)
    dev.get_memory(0x1d0180, length=1)
    dev.get_memory(0x1d0188, length=1)
    dev.get_memory(0x1d01c0, length=1)
    dev.get_memory(0x1d018c, length=1)
    dev.get_memory(0x1d0194, length=3)
    dev.get_memory(0x1d1180, length=5)
    dev.get_memory(0x1d11a4, length=2)
    dev.get_memory(0x10a180, length=6)
    dev.get_memory(0x10a194, length=7)
    dev.get_memory(0x10a1b4, length=9)
    dev.get_memory(0x1da100, length=12)
    dev.get_memory(0x120040, length=2)
    dev.get_memory(0x120128, length=1)
    dev.get_memory(0x12013c, length=1)
    dev.get_memory(0x120110, length=1)
    dev.get_memory(0x120080, length=16)
    dev.get_memory(0x120100, length=48)
    dev.get_memory(0x10b040, length=26)
    dev.get_memory(0x10b0d0, length=1)
    dev.get_memory(0x10b180, length=1)
    dev.get_memory(0x10b1c0, length=5)
    dev.get_memory(0x10b200, length=22)
    dev.get_memory(0x10b480, length=55)
    dev.get_memory(0x10b580, length=10)
    # NBC
    dev.get_memory(0x1a0004, length=1)
    dev.get_memory(0x1a0800, length=3)
    dev.get_memory(0x1a0810, length=6)
    dev.get_memory(0x1a0840, length=2)
    dev.get_memory(0x1a0880, length=1)
    dev.get_memory(0x1a0900, length=3)
    dev.get_memory(0x1a0910, length=6)
    dev.get_memory(0x1a0940, length=2)
    dev.get_memory(0x1a0980, length=2)
    dev.get_memory(0x1a0b00, length=64)
    # system debug
    dev.get_memory(0x1d01c0, length=1)
    dev.get_memory(0x108884, length=1)
    dev.get_memory(0x1058c0, length=2)
    dev.get_memory(0x1d1180, length=1)
    # DDR
    dev.get_memory(0xe0000, length=791)
    dev.get_memory(0xe2000, length=561)
    dev.get_memory(0xe4000, length=2199)
    dev.get_memory(0xe8000, length=791)
    dev.get_memory(0xea000, length=561)
    dev.get_memory(0xec000, length=2199)
    # DDR Path
    dev.get_memory(0x148400, length=3)
    dev.get_memory(0x148420, length=3)
    dev.get_memory(0x148440, length=3)
    dev.get_memory(0x148460, length=3)
    dev.get_memory(0x148480, length=3)
    dev.get_memory(0x1484a0, length=3)
    dev.get_memory(0x1484c0, length=3)
    dev.get_memory(0x1484e0, length=3)
    dev.get_memory(0x148500, length=3)
    dev.get_memory(0x148520, length=3)
    dev.get_memory(0x148540, length=3)
    dev.get_memory(0x148560, length=3)
    dev.get_memory(0x148580, length=3)
    dev.get_memory(0x149104, length=14)
    dev.get_memory(0x137000, length=1)
    dev.get_memory(0x137080, length=5)



    #dev.get_memory(0x109700, length=64)
    #dev.get_memory(0x11a000, length=64)
    #dev.get_memory(0x111000, length=64)
    #dev.get_memory(0x12006c, length=76)
    #dev.get_memory(0x1058c0, length=49)
    #dev.get_memory(0x106840, length=80)
    #dev.get_memory(0x107840, length=4635)
    #dev.get_memory(0x12A0E8, length=13)
    #dev.get_memory(0x137000, length=120)
    #dev.get_memory(0x141020, length=33)
    #dev.get_memory(0x142000, length=152)
    #dev.get_memory(0x144008, length=86)
    #dev.get_memory(0x14700C, length=150)
    #dev.get_memory(0x1472BC, length=18)
    #dev.get_memory(0x14C000, length=18)
    #dev.get_memory(0x14D004, length=343)
    #dev.get_memory(0x14F004, length=776)
    #dev.get_memory(0x193000, length=56)
    #dev.get_memory(0x1A0800, length=275)
    #dev.get_memory(0x1D0180, length=17)
    #dev.get_memory(0x1D1180, length=17)
    #dev.get_memory(0x1D6840, length=51)
    #dev.get_memory(0x2201200C, length=68)
    #dev.get_memory(0x220F0008, length=1)
    #step = 0x4000
    #for addr in range(0x20000, 0xe0000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x340000, 0x360000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x380000, 0x3a0000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x400000, 0x420000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x420000, 0x440000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x440000, 0x460000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x460000, 0x480000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
    #for addr in range(0x60000000, 0x62000000, step):
    #    dev.get_memory(addr=addr, length=int(step/4))
