import tarfile
from os import path

from tools.common import find_files
from tools.gen_version import gen_version
from tools.generate_manifest import gen_manifest


def create_package(sources, output):
    print('Creating framework packae: {}'.format(output))
    prefix = path.join(path.dirname(path.realpath(path.join(__file__, '..'))), '')

    with tarfile.open(output, "w:gz") as tar:
        for source in sources:
            for file in find_files(source):
                if file.startswith(prefix):
                    filename = file[len(prefix):].replace(path.sep, '/')
                    print('Add file to package archive: {}'.format(filename))
                    tar.add(file, arcname=filename)


if __name__ == "__main__":
    gen_version('revvy/fw_version.py')

    mf_sources = ['revvy/', 'revvy.py']
    gen_manifest(mf_sources, 'manifest.json')

    package_sources = ['revvy/', 'data/', 'revvy.py', 'manifest.json']
    create_package(package_sources, 'package.tar.gz')
