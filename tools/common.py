import os
from os import path


def find_files(pathname):
    pathname = path.realpath(pathname)
    if path.isfile(pathname):
        yield pathname
    elif path.isdir(pathname):
        for f in os.listdir(pathname):
            if f != '__pycache__':
                for sub in find_files(path.join(pathname, f)):
                    yield sub
