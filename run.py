#!/usr/bin/env python
# coding=utf-8
import argparse
import os
import re
import subprocess
import sys

from lib.driver.rest_server.reset_server import APP
from lib.driver.rest_server.resource.models.ftp_server import thread_start_ftp_server
from lib.driver.test_framework.database import update_abnormal_end_tests
from lib.driver.test_framework.test_case import TestCase
from lib.driver.test_framework.test_os_reboot import OsRebootHandler
from lib.driver.test_framework.test_power_cycle import PowerCycleHandler
from lib.driver.test_framework.test_suite import TestSuite
from lib.tool.cnexssdmanager.cnex_ssd_manager import CnexSSDManager

sys.path.append(os.path.join(os.path.dirname(__file__)))


def add_sub_argument_group(subparsers, name, handler_function):
    regression_parser = subparsers.add_parser(name, help='%s tests executor' % name)
    regression_required_arguments = regression_parser.add_argument_group('required arguments')
    if name != 'testfile':
        regression_required_arguments.add_argument('--name', '-n', type=str, default="testcase", required=False,
                                                   help='test suite ,test case name or operation name')
        regression_required_arguments.add_argument('--variables', '-v', type=str, default=None, required=False,
                                                   help='user variables, format: var1:value1,var2:value3')
        regression_required_arguments.add_argument('--list', '-l', type=str, default=None, required=False,
                                                   help='list and filter test case')
        regression_required_arguments.add_argument('--fw', '-f', type=str, default=None, required=False,
                                                   help='fw path for upgrade')
        regression_required_arguments.add_argument('--stop', '-s', action='store_true', help='stop on fail?')
    else:
        regression_required_arguments.add_argument('name', help='test file name')
        regression_required_arguments.add_argument('args', nargs=argparse.REMAINDER, help='remain arguments')
    regression_required_arguments.add_argument('--third', '-t', action='store_true', help='Third SSD')
    regression_parser.set_defaults(executor_function=handler_function)


def create_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    add_sub_argument_group(subparsers, 'testsuite', test_suite_handle)
    add_sub_argument_group(subparsers, 'testcase', test_case_handle)
    add_sub_argument_group(subparsers, "testfile", test_file_handle)
    add_sub_argument_group(subparsers, 'start', start_rest_server)
    add_sub_argument_group(subparsers, 'operate', operate_handle)
    add_sub_argument_group(subparsers, "powercycle", power_cycle_handler)
    add_sub_argument_group(subparsers, "osreboot", os_reboot_handler)
    add_sub_argument_group(subparsers, "clean", clean)

    return parser


def clean(args):
    print(args)
    if input('Make sure to delete all logs (y/n)? ').lower().startswith('y'):
        cmd = 'rm ./log/* -rf'
        print(cmd)
        subprocess.call(cmd, shell=True)


def get_test_file(file):
    for path, _, files in os.walk(os.path.join(os.path.dirname(__file__), 'testfile')):
        for _file in files:
            if file in _file:
                return os.path.join(path, _file)
    raise AssertionError('Cannot find test file!')


def test_file_handle(args):
    cmd = 'python3 {}'.format(get_test_file(args.name))
    if args.args:
        cmd = '{} {}'.format(cmd, ' '.join(args.args))
    status = subprocess.call(cmd, shell=True)
    assert status == 0, 'Run test file: {} failed!'.format(args.name)


def start_rest_server(args):
    update_abnormal_end_tests()
    thread_start_ftp_server()
    APP.run(host="0.0.0.0")


def test_suite_handle(args):
    test_suite = TestSuite(args.stop)
    if args.list is not None:
        rets = test_suite.list_and_filter_tests(args.list)
        for item in rets:
            print(item)
    else:
        exit(test_suite.run(args.name))


def operate_handle(args):
    ssd_operation = CnexSSDManager()
    if args.name == "upgrade":
        ssd_operation.upgrade_fw(args.fw)


def test_case_handle(args):
    test_case = TestCase(args.name)
    if args.list is not None:
        rets = test_case.list_and_filter_tests(args.list)
        for item in rets:
            print(item)
    else:
        result = test_case.run()
        exit(result["status"])


def power_cycle_handler(args):
    power_cycle = PowerCycleHandler(args.name)
    status = power_cycle.run(args.name)
    exit(status)


def os_reboot_handler(args):
    os_reboot = OsRebootHandler()
    os_reboot.run(args.name)


def add_globals(args):
    os.environ["root_path"] = os.path.join(os.path.dirname(__file__))
    os.environ["working_path"] = os.getcwd()
    os.environ["PYTHONPATH"] = os.getcwd()
    os.environ['PYTHONUNBUFFERED'] = "TRUE"
    os.environ['THIRD_SSD'] = str(args.third)
    if 'variables' in args and args.variables is not None:
        str_variable = args.variables
        rets = re.findall(r"(\w+)\:([^\,]+)", str_variable)
        for item in rets:
            os.environ[str(item[0])] = str(item[1])


def run():
    parser = create_parser()
    args = parser.parse_args()
    add_globals(args)
    args.executor_function(args)


if __name__ == '__main__':
    run()
