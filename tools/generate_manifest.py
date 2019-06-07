#!/usr/bin/python3

# create manifest file containing the version and individual file checksum values
# start using 'python -m tools.generate_manifest' from the root directory
import json
from datetime import datetime
from os import path
from revvy.fw_version import FRAMEWORK_VERSION
from tools.common import find_files, file_hash


def gen_manifest(sources, output):
    print('Creating manifest file: {}'.format(output))
    prefix = path.join(path.dirname(path.realpath(path.join(__file__, '..'))), '')

    hashes = {}

    for source in sources:
        for file in find_files(source):
            if file.startswith(prefix) and file.endswith('.py'):
                filename = file[len(prefix):].replace(path.sep, '/')
                checksum = file_hash(file)
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
    manifest_source = ['revvy/', 'revvy.py']
    gen_manifest(manifest_source, 'manifest.json')
