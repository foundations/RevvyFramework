#!/usr/bin/python3
import os


def gen_version(out_file):
    template = '# This file is generated before each commit\n' \
               'FRAMEWORK_VERSION = "0.1.{{VERSION}}"\n'

    version = os.popen('git rev-list --count HEAD').read()
    version = version.strip()

    branch = os.popen('git rev-parse --abbrev-ref HEAD').read()
    branch = branch.strip()

    if branch != 'master':
        template = template.replace('{{VERSION}}', '{{VERSION}}-{{BRANCH}}')

    print("Generating version file for revision {}".format(version))

    with open(out_file, 'w') as out:
        out.write(template.replace("{{BRANCH}}", branch).replace("{{VERSION}}", version))


if __name__ == "__main__":
    file = "revvy/fw_version.py"
    gen_version(file)
