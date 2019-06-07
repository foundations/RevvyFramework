#!/usr/bin/python3

# check whether the current package files are valid according to the manifest
# start using 'python -m tools.check_manifest' from the root directory
import json

from tools.common import file_hash


def check_manifest(manifest_file):
    print('Checking manifest file: {}'.format(manifest_file))

    with open(manifest_file) as mf:
        manifest = json.load(mf)
    hashes = manifest['files']

    for file in hashes:
        expected = hashes[file]
        hash_value = file_hash(file)

        if hash_value != expected:
            print('Integrity check failed for {}'.format(file))
            return False

    return True


if __name__ == "__main__":
    if check_manifest('manifest.json'):
        print('Valid')
    else:
        print('Invalid')
