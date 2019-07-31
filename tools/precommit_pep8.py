#!/usr/bin/env python
import re
import subprocess
import sys


def system(*args, **kwargs):
    kwargs.setdefault('stdout', subprocess.PIPE)
    proc = subprocess.Popen(args, **kwargs)
    out, err = proc.communicate()
    return out.decode("utf-8") if out else None


def main():
    modified = re.compile('^[AM]+\\s+(?P<name>.*\\.py)', re.MULTILINE)
    files = system('git', 'status', '--porcelain')
    files = modified.findall(files)
    output = system('pycodestyle', '--max-line-length=120', *files)

    if output:
        print(output)
        sys.exit(1)


if __name__ == '__main__':
    main()
