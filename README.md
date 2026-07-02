# Production Automation

This is the automation platform for production testing. Include test case and tools.
It is also support run performance test and TestRail tests.
For more help information, please check the help documentation "Production_Automation_quickly_start.docx"


## Install
* Python 3.7, the first step is make sure python is ready in your system, required > python 3.7
* Python package, Please run "install.py" to install necessary python packages.

## how to search test case
* command Format: python run.py testcase -l key_word
* For example:
    - python run.py testcase -l r5

## How to run test case locally

* command format: python run.py testcase -n $casename -v var1:value1,var2:value3
* For example:
    - python run.py testcase -n test_flash_with_storscore.py -v fw_bin:"d:\\1.bin"

## How to run test suite locally

* command format: python run.py testsuite -n $testsuitename -v var1:value1,var2:value3
* For example:
    - python run.py testsuite -n fio -v fw_bin:"d:\\1.bin"


## How to UI application remote run tests, recommended use this way to run tests
* Start server on test environment(with administrator or root): python run.py start
* copy the UI application to your office compute(it is at \bin\Production_client.exe), open the application
* Scan the environment with IP address
* Run tests in the remote test environment
* More introduction please check the help documentation

## How to config test suite

* test suite format:
<br>name: fio_test (**test suite name**)
<br>description: run fio test for debug testsuite (**test suite description**)
<br>loop: 1  (**loops of test suite**)
<br>cases:  (**test cases list**)
<br>&#8194;&#8194;\- script: test_fio_windows.py:TestFioWindows.test_rand_mix_rw_50_50 (**test case name**)
<br>&#8194;&#8194;&#8194;&#8194;duration: 0  (**test case duration**)
<br>&#8194;&#8194;&#8194;&#8194;loop: 1  (**loops of test case**)
<br>&#8194;&#8194;\- script: test_fio_windows.py:TestFioWindows.test_rand_mix_rw_70_30
<br>&#8194;&#8194;&#8194;&#8194;duration: 0
<br>&#8194;&#8194;&#8194;&#8194;loop: 1


## Readme about test cases

### FIO
* windows FIO, Please install fio before test, at: Tools\fio


### StorScore cases
* Before you run StorScore test cases, you should install  StorScore dependencies, some "external" software components.
* You can find these dependencies at: \\\172.29.190.1\\nvme\\public\\product_test\\StoreScore\\storscore_env

### TestReboot
* This case need two computes
* One have SSD device need to create a BAT file for run IOMeter, and add this bat file to windows system startup folder
   and use administrator permission to run this bat, when system startup
* Another compute run test case(TestReboot.py) to reboot the compute that have SSD.  

### TestBurnIn
* Before run test case please install BurnIn, the install package Shares:\QA\Test_Tools\burnIn test v9.0

### more test case please check the test case folder

## NVMe() 使用指南
* TestCase默认实例化NVMe
    ```
    self.nvme = NVMe(nsid=1)
    ```
* 实例化后可以直接使用部分常量(具体请查看@property的类方法)
    ```
    cntid/nsid/slot_dev/char_dev/block_dev/pcie/id_ns/id_ctrl/active_nsid_list/max_valid_nsid/max_lba/flbas/is_dif/lbads/lbams/lbaf_list
    ```
* 以下命令更新NVMe
    ```
    scan_devices/waiting_device_ready
    ```
* 以下命令默认调用ctrl reset和更新NVMe的方法
    ```
    format/attach_ns/detach_ns
    ```
* 尽量引用self.nvme，确保信息同步，比如
    ```
    traffic = LBAOperate(dev=self.nvme)
    link = Link(dev=self.nvme)
    clearbb = ClearBB(nvme=self.nvme)
    ```
* 执行plp/reset/hotplug等操作后，不要重新实例化self.nvme，选择以下任一命令更新
    ```
    # 300s内每隔5s检查并更新device，成功直接返回，超时raise error
    self.nvme.waiting_device_ready(timeout=300, interval=5)

    # 检查并更新device，出错raise error
    self.nvme.scan_devices()
    ```
* 如果nsid有变动，使用以下命令更新
    ```
    self.nvme.scan_devices(nsid=2)
    ```
* 已知问题/限制
    ```
    * read/write/read_passthru/write_passthru/compare，nlb>64，偶尔报错 OSError(22) Invalid Argument，驱动问题
    * create_io_cq/create_io_sq 创建的queue不能发I/O命令，驱动限制
    ```