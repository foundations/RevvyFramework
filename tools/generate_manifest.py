#!/usr/bin/python3

# create manifest file containing the version and individual file checksum values
# start using 'python -m tools.generate_manifest' from the root directory
import json
from datetime import datetime
from hashlib import md5
from os import listdir, path
from revvy.fw_version import FRAMEWORK_VERSION


def find_files(pathname):
    pathname = path.realpath(pathname)
    if path.isfile(pathname):
        yield pathname
    elif path.isdir(pathname):
        for f in listdir(pathname):
            if f != '__pycache__':
                for sub in find_files(path.join(pathname, f)):
                    yield sub


prefix = path.join(path.dirname(path.realpath(path.join(__file__, '..'))), '')

hashes = {}

sources = ['revvy/', 'revvy.py']
for source in sources:
    for file in find_files(source):
        if file.startswith(prefix) and file.endswith('.py'):
            filename = file[len(prefix):].replace(path.sep, '/')
            hash_fn = md5()
            with open(file, "rb") as f:
                hash_fn.update(f.read())
            hashes[filename] = hash_fn.hexdigest()

manifest = {
    'version': FRAMEWORK_VERSION,
    'manifest-version': 1.0,
    'generated': datetime.now().isoformat(),
    'files': hashes
}

with open('manifest.json', "w") as mf:
    json.dump(manifest, mf, indent=4)
