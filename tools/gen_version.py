#!/usr/bin/python3
import os

file = "fw_version.py"
template = """
# This file is generated before each commit
FRAMEWORK_VERSION = 0.1-r{{VERSION}}
"""

version = os.popen('git rev-list --count HEAD').read()
version = version.strip()

branch = os.popen('git rev-parse --abbrev-ref HEAD').read()
branch = branch.strip()

if branch != 'master':
    template = template.replace('{{VERSION}}', '{{VERSION}}-{{BRANCH}}')

print("Generating version file for revision {}".format(version))

with open(file, 'w') as out:
    out.write(template.replace("{{BRANCH}}", branch).replace("{{VERSION}}", version))
