#!/usr/bin/python
import os
import re
import subprocess
import time
from collections import OrderedDict
from optparse import OptionParser


class TNVMETest(object):
    def __init__(self, sgr=0, ngr=40, rev=1.2, tnvme_path=None, log_path=None):
        self.sgr = sgr
        self.ngr = ngr
        self.rev = rev
        self.tnvme_path = tnvme_path
        self.log_path = log_path
        file_name = os.path.join(self.log_path, "resultLogs.txt")
        self.log_fp = open(file_name, "wb")
        self.logname = os.path.join(self.log_path, 'runLog_')
        self.tlist = self.__initList(self.sgr, self.ngr)

    def __del__(self):
        self.log_fp.close()

    def __initList(self, sgr, ngr):
        tlist = OrderedDict()  # {tc_name:[status,descriptor]}
        cmd = self.__genTnvmeCmd("-s")
        tmp = os.popen(cmd)
        output = tmp.read()
        tc_list = output.split("\n")
        group_name = -1
        for i in range(len(tc_list)):
            match = re.search("^(\d+): +(.+)$", tc_list[i])
            if match:
                group_name = match.group(1)
                # print "Group: %s, tc_num: %d, stat_num: %d"%(group_name,len(tc_name),len(tc_stat))
            if (int(group_name) >= sgr + ngr) and ngr != 0:
                return tlist
            if (int(group_name) >= sgr):
                match = re.search("^ +([\d\.]+): +(.+)$", tc_list[i])
                if match:
                    tc_tmp = "%s:%s" % (group_name, match.group(1))
                    # print "tc_num: %s, des: %s"%(tc_tmp,match.group(2))
                    tlist[tc_tmp] = [0, match.group(2)]
        return tlist

    def __genGrouplist(self, tc):
        glist = []
        for i in self.tlist.keys():
            if tc in i:
                glist.append(i)
        return glist

    def __excTest(self, tc):
        group_list = self.__genGrouplist(tc)
        self.__getTNVMEResult(tc, group_list)

    def runGroupTest(self):
        group_name = ''
        for i in self.tlist.keys():
            newg = i.split(":")[0]
            if newg != group_name:
                print("Start Group test: %s" % newg)
                self.__excTest(newg)
            group_name = newg

    def runSingleTest(self):
        for i in self.tlist.keys():
            if self.tlist[i][0] == 0:
                self.__excTest(i)

    def runTest(self):
        # self.runGroupTest()
        self.runSingleTest()
        return self.__saveResult()

    def __saveResult(self):
        file_name = os.path.join(self.log_path,
                                 "tnvmeResult_%s.txt" % (time.strftime('%Y%m%d', time.localtime(time.time()))))
        FB = open(file_name, "w+")
        FB.write("Test_Name     Descript%78sStatus" % (""))
        FB.write("\n")
        fail_cnt = 0
        for i in self.tlist.keys():
            if self.tlist[i][0] == 0:
                result = "Undo"
            elif self.tlist[i][0] == 1:
                result = "Passed"
            elif self.tlist[i][0] == 2:
                result = "Failed"
                fail_cnt += 1
            elif self.tlist[i][0] == 3:
                result = "Skipped"
            elif self.tlist[i][0] == 4:
                result = "Informative"
            else:
                raise Exception("Test case[%s] status[%d] is not right" % (i, self.tlist[i][0]))
            FB.write("%s    %s       %s " % (format(i, "<10"), format(self.tlist[i][1], "<80"), result))
            FB.write("\n")
        FB.close()
        return (fail_cnt != 0)

    def __extractResult(self, fp):
        fp.seek(-2000, 2)
        off = fp.tell()
        line = fp.readline()
        print("off:%d, str: %s" % (off, line))
        mat_flag = 0
        res = ""
        str_arr = []
        while line:
            # print line
            line = fp.readline()
            str_arr.append(line.decode())
        res = "".join(str_arr)
        res = re.sub("\n", " #", res)
        res = re.sub(".*: Iteration SUMMARY", "Iteration SUMMARY", res)
        return res

    def __getTNVMEResult(self, tc, tc_name):
        stat_list = {}
        sub_list = []
        fail_list = []
        skip_list = []
        # print stat_list
        cmd = self.__genTnvmeCmd("--test=%s" % tc)
        for i in range(len(tc_name)):
            # print tc_name[i]
            stat_list[tc_name[i]] = 0
        file_name = self.logname + tc + u'.log'
        fp = open(file_name, "wb+")
        res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=fp, close_fds=True)
        (out, e) = res.communicate()
        print("%s finished, Start collect Information..." % cmd)
        self.log_fp.write(cmd.encode("utf-8"))
        self.log_fp.write("\n".encode("utf-8"))
        self.log_fp.write(out)
        match = self.__extractResult(fp)
        fp.close()
        print("Filtering useless information...")
        mat = re.search(
            "passed +: (\d+) .*failed +: (\d+) .*skipped +: (\d+) .*informative +: (\d+) .*total tests +: +(\d+)",
            match)
        if not mat:
            print("%s didn't run successfully" % cmd)
            return stat_list
        p_num = int(mat.group(1))
        f_num = int(mat.group(2))
        s_num = int(mat.group(3))
        i_num = int(mat.group(4))
        t_num = int(mat.group(5))
        if t_num != (p_num + f_num + s_num + i_num):
            raise Exception(
                "TC number is not right[Total: %s, Passed: %s, Failed: %s, Skipped: %s, Informative: %s]" % (
                t_num, p_num, f_num, s_num, i_num))
        print("passed      : %s" % p_num)
        print("failed      : %s" % f_num)
        print("skipped     : %s" % s_num)
        print("informative : %s" % i_num)
        print("total       : %s" % t_num)
        print("Get TC number finished")
        match = re.sub(".*Detailed Iteration SUMMARY #", "", match)
        sub_list = match.split(" #")
        for i in range(len(sub_list)):
            mat = re.search("Tests Failed", sub_list[i])
            if mat:
                fail_flag = 1
                skip_flag = 0
            mat = re.search("Tests Skipped", sub_list[i])
            if mat:
                fail_flag = 0
                skip_flag = 1
            mat = re.search(".* (\d+:\d+\.\d+\.\d+)", sub_list[i])
            if mat:
                if mat.group(1) in stat_list:
                    if fail_flag == 1:
                        # fail_list.append(mat.group(1))
                        stat_list[mat.group(1)] = 2
                    if skip_flag == 1:
                        stat_list[mat.group(1)] = 3
                        # skip_list.append(mat.group(1))
        print("Mark failed and skipped tc status finished")
        # print tc_name
        # print stat_list
        if i_num == 0:
            stat = 1
            # print "t_num: %d"%t_num
            if len(tc_name) == 1:
                tc = tc_name[0]
                if (f_num != 0) | (s_num != 0):
                    stat = 2
                if stat_list[tc] == 0:
                    stat_list[tc] = stat
            else:
                for i in range(t_num):
                    tc = tc_name[i]
                    if stat_list[tc] == 0:
                        stat_list[tc] = 1
                    # print "%s: %d"%(tc,stat_list[tc])
        elif p_num == 0:
            stat = 4
            if len(tc_name) == 1:
                tc = tc_name[0]
                if (f_num != 0) | (s_num != 0):
                    stat = 2
                if stat_list[tc] == 0:
                    stat_list[tc] = stat
            else:
                for i in range(t_num):
                    tc = tc_name[i]
                    if stat_list[tc] == 0:
                        stat_list[tc] = stat
        else:
            stat = 1
            if len(tc_name) == 1:
                tc = tc_name[0]
                if stat_list[tc] == 0:
                    stat_list[tc] = stat
        print("Mark passed and informative tc status finished")
        return self.__markResult(stat_list)

    def __markResult(self, stat_list):
        for i in stat_list.keys():
            if i not in self.tlist.keys():
                print("Testcase: %s not exist!!" % i)
                return 1
            if self.tlist[i][0] == 0:
                self.tlist[i][0] = stat_list[i]
            else:
                if self.tlist[i][0] != stat_list[i]:
                    print("Test result Change[tc: %s][ex_stat: %s, now_stat: %s]" % (i, self.tlist[i][0], stat_list[i]))
                    self.log_fp.write(
                        "Test result Change[tc: %s][ex_stat: %s, now_stat: %s]\n" % (i, self.tlist[i][0], stat_list[i]))
        return 0

    def __genTnvmeCmd(self, tc):
        # TNVME_CMD = "/home/nvme/public/iol_interact-1.2.2/nvme/tnvme/tnvme"
        # TNVME_CMD = r"/home/nvme/public/NVMe.Plugfest/NVMe.Plugfest8/INTERACT-PC/PC_Edition_PCIe/iol_interact-8.0b/tnvme/tnvme"

        cmd = "%s --rev=%s %s" % (self.tnvme_path, self.rev, tc)
        return cmd


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-n", "--num", type="int", dest="num", default=0, help="Number of Group to run")
    parser.add_option("-s", "--sgroup", type="int", dest="sgr", default=0, help="start of Group to run")
    try:
        (options, args) = parser.parse_args()
        num = options.num
        sgr = options.sgr
        TNVME_CMD = r"/mnt/public/NVMe.Plugfest/NVMe.Plugfest8/INTERACT-PC/PC_Edition_PCIe/iol_interact-8.0b/tnvme/tnvme"
        tnvme = TNVMETest(sgr, num, tnvme_path=TNVME_CMD)
        tnvme.runTest()

    except Exception as e:
        print("Test Failed")
        print(e)
        exit(1)
