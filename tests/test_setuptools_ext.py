import shutil
import zipfile
from pathlib import Path

import pytest
from wimpy import working_directory

import setuptools_ext


here = Path(__file__).absolute().parent


@pytest.fixture(autouse=True)
def in_source_tree(tmp_path):
    shutil.copy2(here / "example_project.toml", tmp_path / "pyproject.toml")
    shutil.copy2(here / "example_readme.rst", tmp_path / "README.rst")
    with working_directory(tmp_path):
        yield tmp_path


expected_metadata = """\
Metadata-Version: 2.1
Name: example-proj
Version: 0.1
Summary: example summary
Home-page: https://example.org/
Author: Wim Glenn
Author-email: hey@wimglenn.com
License: MIT
Project-URL: homepage, https://example.org/
Description-Content-Type: text/x-rst
Supported-Platform: RedHat 8.3
Requires-External: C
Requires-External: libpng (>=1.5)
Requires-External: make; sys_platform != "win32"

this is the first line of the README.rst file
this is the second line of the README.rst file

"""


def test_build_wheel(in_source_tree):
    whl = setuptools_ext.build_wheel(wheel_directory=in_source_tree)
    with zipfile.ZipFile(in_source_tree / whl) as zf:
        txt = zf.read("example_proj-0.1.dist-info/METADATA").decode()
    assert txt == expected_metadata
