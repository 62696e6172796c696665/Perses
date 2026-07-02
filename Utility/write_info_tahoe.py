import argparse
import sys
import os
import datetime

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


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='nvme driver set streams for io')
    parser.add_argument('--block_device', '-d', type=str, default="/dev/nvme0n1", required=False, help='<device>')
    parser.add_argument('--slot', '-s', type=str, required=False, help='01:00.0')
    parser.add_argument('--show_value', '-v', type=str, default=f"start test at: {str(datetime.date.today())}",
                        required=True, help='')
    args = parser.parse_args()
    print(args.block_device)
    print(args.slot)
    print(args.show_value)
    assert args.slot not in [None, 'None', "", "null"] or args.block_device not in [None, 'None', "", "null"]
    if args.slot not in [None, 'None', "", "null"]:
        nvme = Tahoe(slot=args.slot)
    else:
        nvme = Tahoe(block=args.block_device)
    nvme.vu_cmd.show_test_case(args.show_value)