#/usr/bin/python3
import os

file = "../fw_version.py"
template = """
# This file is generated before each commit
FRAMEWORK_VERSION = {{VERSION}}
"""

version = os.popen('git rev-list --count HEAD').read()
version = version.strip()
with open(file, 'w') as out:
	out.write(template.replace("{{VERSION}}", version))