#!/usr/bin/python3

# create manifest file containing the version and individual file checksum values
# start using 'python -m tools.generate_manifest' from the root directory
import json
from datetime import datetime
from hashlib import md5
from os import path
from revvy.fw_version import FRAMEWORK_VERSION
from tools.common import find_files


def gen_manifest(sources, output):
    print('Creating manifest file: {}'.format(output))
    prefix = path.join(path.dirname(path.realpath(path.join(__file__, '..'))), '')

    hashes = {}

    for source in sources:
        for file in find_files(source):
            if file.startswith(prefix) and file.endswith('.py'):
                filename = file[len(prefix):].replace(path.sep, '/')
                hash_fn = md5()
                with open(file, "rb") as f:
                    hash_fn.update(f.read())
                checksum = hash_fn.hexdigest()
                print('Add file to manifest: {} (checksum: {})'.format(filename, checksum))
                hashes[filename] = checksum

    manifest = {
        'version': FRAMEWORK_VERSION,
        'manifest-version': 1.0,
        'generated': datetime.now().isoformat(),
        'files': hashes
    }

    with open(output, "w") as mf:
        json.dump(manifest, mf, indent=4)


if __name__ == "__main__":
    sources = ['revvy/', 'revvy.py']
    output = 'manifest.json'
    gen_manifest(sources, output)
