from __future__ import unicode_literals

import os
import sys
import zipfile
import pytest
import setuptools_ext

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


here = Path(__file__).absolute().parent


example_project = """\
[build-system]
requires = ["setuptools-ext"]
build-backend = "setuptools_ext"

[project]
name = "example-proj"
authors = [
    {name = "Wim Glenn"},
    {email = "hey@wimglenn.com"},
]
description = "example summary"
readme = "README.rst"
version = "0.1"
license = {text = "MIT"}

[project.urls]
homepage = "https://example.org/"

[tool.setuptools-ext]
requires-external = [
    "C",
    "libpng (>=1.5)",
    'make; sys_platform != "win32"'
]
supported-platform = "RedHat 8.3"
bogus-field = "this will be ignored"
"""

example_readme = """\
this is the first line of the README.rst file
this is the second line of the README.rst file"""


# only used on py2, because setuptools doesn't support pyproject.toml metadata there
example_setup_cfg = """\
[metadata]
name = example-proj
author = Wim Glenn
author_email = hey@wimglenn.com
version = 0.1
license = MIT
description = example summary
long_description = file: README.rst
long_description_content_type = text/x-rst
project_urls =
    homepage = https://example.org/
"""


expected_metadata = """\
Metadata-Version: 2.1
Name: example-proj
Version: 0.1
Summary: example summary
Author: Wim Glenn
Author-email: hey@wimglenn.com
License: MIT
Project-URL: homepage, https://example.org/
Description-Content-Type: text/x-rst
Requires-External: C
Requires-External: libpng (>=1.5)
Requires-External: make; sys_platform != "win32"
Supported-Platform: RedHat 8.3

this is the first line of the README.rst file
this is the second line of the README.rst file
"""


@pytest.fixture(autouse=True)
def in_source_tree(tmp_path):
    tmp_path.joinpath("pyproject.toml").write_text(example_project)
    tmp_path.joinpath("README.rst").write_text(example_readme)
    if sys.version_info.major < 3:
        tmp_path.joinpath("setup.cfg").write_text(example_setup_cfg)
    prev = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        yield tmp_path
    finally:
        os.chdir(prev)


def test_build_wheel(in_source_tree):
    whl = setuptools_ext.build_wheel(wheel_directory=str(in_source_tree))
    with zipfile.ZipFile(str(in_source_tree / whl)) as zf:
        txt = zf.read("example_proj-0.1.dist-info/METADATA").decode()
    assert txt.rstrip() == expected_metadata.rstrip()
