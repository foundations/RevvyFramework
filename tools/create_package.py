# start using 'python -m tools.create_package' from the root directory
import json
import tarfile
import os
import shutil
from os import path

from revvy.functions import file_hash
from revvy.fw_version import FRAMEWORK_VERSION
from tools.common import find_files
from tools.generate_manifest import gen_manifest


def create_package(sources, output):
    print('Creating framework package: {}'.format(output))
    prefix = path.join(path.dirname(path.realpath(path.join(__file__, '..'))), '')

    with tarfile.open(output, "w:gz") as tar:
        for source in sources:
            for file in find_files(source):
                if file.startswith(prefix):
                    filename = file[len(prefix):].replace(path.sep, '/')
                    print('Add file to package archive: {}'.format(filename))
                    tar.add(file, arcname=filename)


if __name__ == "__main__":
    print('Downloading requirements')
    os.popen('pip3 download -r install/requirements.txt -d install/packages').read()

    manifest_source = [
        'data/',
        'install/requirements.txt',
        'install/packages/',
        'revvy/',
        'revvy.py'
    ]
    gen_manifest(manifest_source, 'manifest.json')

    package_sources = [
        'revvy/',
        'install/requirements.txt',
        'install/packages/',
        'data/',
        'revvy.py',
        '__init__.py',
        'tools/',
        'manifest.json'
    ]
    package_path = 'install/framework-{}.tar.gz'.format(FRAMEWORK_VERSION.replace('/', '-'))
    data_path = 'install/framework.data'
    meta_file = 'install/framework.meta'
    create_package(package_sources, package_path)

    shutil.copy(package_path, data_path)

    print('Remove downloaded packages')
    shutil.rmtree('install/packages')

    filehash = file_hash(package_path)
    filesize = os.stat(package_path).st_size

    with open(meta_file, "w") as mf:
        json.dump({'length': filesize, 'md5': filehash}, mf)

    print('Package created: {}'.format(package_path))
    print('Package checksum: {}'.format(filehash))
