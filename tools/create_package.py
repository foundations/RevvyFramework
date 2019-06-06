# start using 'python -m tools.create_package' from the root directory

import tarfile
import os
import shutil
from os import path

from revvy.fw_version import FRAMEWORK_VERSION
from tools.common import find_files
from tools.generate_manifest import gen_manifest


def create_package(sources, output):
    print('Downloading requirements')
    os.popen('pip3 download -r install/requirements.txt -d install/packages').read()

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
    mf_sources = ['revvy/', 'revvy.py']
    gen_manifest(mf_sources, 'manifest.json')

    package_sources = [
        'revvy/',
        'data/',
        'install/requirements.txt',
        'install/packages/',
        'revvy.py',
        '__init__.py',
        'manifest.json'
    ]
    create_package(package_sources, 'install/framework-{}.tar.gz'.format(FRAMEWORK_VERSION))

    print('Remove downloaded packages')
    shutil.rmtree('install/packages')
