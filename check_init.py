import os
import sys


EXCLUDE_PATH = [
    'kernel3.10'
]


def check_exclude(path):
    for exclude in EXCLUDE_PATH:
        if exclude in path:
            return True
    return False

def check_init(root):
    for path, _, files in os.walk(os.path.join(os.path.dirname(__file__), root)):
        if check_exclude(path) is False and '__init__.py' not in files:
            print(f'{path} does not have __init__.py')
            # filename = os.path.join(path, '__init__.py')
            # os.system(f'touch {filename}')
            sys.exit(1)


if __name__ == '__main__':
    check_init('lib')
    check_init('testcase')
    sys.exit(0)
