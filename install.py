import os
import sys

python_package_list = [
    "nose",
    "pyyaml",
    "setuptools-rust",
    "paramiko",
    "checksumdir",
    "xlrd",
    "flask",
    "flask-restful",
    "requests",
    "func_timeout",
    "xlsxwriter",
    "pyyaml",
    "pycurl",
    "tornado",
    "production_rest_client",
    "automation_rest_server",
    "PyMySQL",
    "pyftpdlib",
    "openpyxl",
    "tqdm",
    "psutil",
    "retry",
    "pexpect",
    "pyserial",
    "cnextb",
    "quarchpy==2.0.20"
]


def get_python_version():
    version = sys.version
    if "2.7" in version or "2.6" in version:
        system = "python2"
    else:
        system = "python3"
    return system


def install_auto_it():
    if "win" in sys.platform:
        os.system("cd {} && python setup.py install".format(
            os.path.join(os.path.dirname(__file__), "tools", "PyAutoIt-0.4")))


def install_packages():
    python_version = get_python_version()
    if python_version == "python2":
        pip_name = "pip"
    else:
        pip_name = "pip3"
    cmd = "{} install --upgrade pip".format(pip_name)
    os.system(cmd)
    for package_name in python_package_list:
        cmd = "{} install {}".format(pip_name, package_name)
        os.system(cmd)


if __name__ == '__main__':
    install_packages()
    install_auto_it()
