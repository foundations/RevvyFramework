import os
from hashlib import md5
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


def file_hash(file):
    hash_fn = md5()
    with open(file, "rb") as f:
        hash_fn.update(f.read())
    return hash_fn.hexdigest()
