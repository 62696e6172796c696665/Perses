import argparse
import sys
import os

sys.path.append("....")
sys.path.append("...")
sys.path.append("..")
sys.path.append(".")
currentPath = os.path.split(os.path.realpath(__file__))[0]
projectRootPath = os.path.abspath(os.path.join(currentPath, '..'))
utilPath = os.path.join(projectRootPath, 'util')
sys.path.append(projectRootPath)
sys.path.append(utilPath)

from lib.driver.nvme import Tahoe

help_mode = """mode:
        - 1: without non-streams,
        - 2: use all streams id(e.g. 0,1,2,3),
        - default: 0 (non-streams)
"""


help_lba = """lba:
        - 0: drv assign streams id randomly,
        - over 0: drv assign streams id by lba
"""


help_count = """
count: supported number of streams, default: 0 (non-streams)
"""


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='nvme driver set streams for io')
    parser.add_argument('--block_device', '-d', type=str, default="/dev/nvme0n1", required=True, help='<device>')
    parser.add_argument('--count', "-c", default=0, required=True, type=int, help=help_count)
    parser.add_argument('--mode', "-m", default=0, required=True, type=int, help=help_mode)
    parser.add_argument('--lba', "-l", default=0, required=True, type=int, help=help_mode)
    args = parser.parse_args()
    print(args.block_device)
    print(args.count)
    print(args.mode)
    print(args.lba)
    nvme = Tahoe(block=args.block_device)
    nvme.set_stream(count=args.count, mode=args.mode, lba=args.lba)