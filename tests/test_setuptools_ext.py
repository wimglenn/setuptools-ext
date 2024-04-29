import os
import tarfile
import zipfile
from pathlib import Path

import pytest

import setuptools_ext


here = Path(__file__).absolute().parent


pyproject_full = """\
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

[project.optional-dependencies]
all = ["typing-extensions <5,>=4.2 ; python_version < '3.8'"]

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
this is the second line of the README.rst file — and it has non-ascii in it"""


pyproject_minimal = """\
[build-system]
requires = ["setuptools-ext"]
build-backend = "setuptools_ext"

[tool.setuptools-ext]
requires-external = [
    "C",
    "libpng (>=1.5)",
    'make; sys_platform != "win32"'
]
supported-platform = "RedHat 8.3"
bogus-field = "this will be ignored"
"""


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

[options.extras_require]
all =
    typing-extensions <5,>=4.2 ; python_version < '3.8'
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
Provides-Extra: all
Requires-Dist: typing-extensions <5,>=4.2 ; (python_version < "3.8") and extra == 'all'
Requires-External: C
Requires-External: libpng (>=1.5)
Requires-External: make; sys_platform != "win32"
Supported-Platform: RedHat 8.3

this is the first line of the README.rst file
this is the second line of the README.rst file — and it has non-ascii in it
"""


@pytest.fixture(autouse=True)
def in_srctree(tmp_path):
    tmp_path.joinpath("README.rst").write_text(example_readme, encoding="utf8")
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(prev)


def test_build_wheel_pyproject_toml(in_srctree):
    in_srctree.joinpath("pyproject.toml").write_text(pyproject_full, encoding="utf8")
    whl = setuptools_ext.build_wheel(wheel_directory=str(in_srctree))
    with zipfile.ZipFile(in_srctree / whl) as zf:
        txt = zf.read("example_proj-0.1.dist-info/METADATA").decode()
    assert txt.rstrip() == expected_metadata.rstrip()


def test_build_wheel_setup_cfg(in_srctree):
    in_srctree.joinpath("pyproject.toml").write_text(pyproject_minimal, encoding="utf8")
    in_srctree.joinpath("setup.cfg").write_text(example_setup_cfg, encoding="utf8")
    whl = setuptools_ext.build_wheel(wheel_directory=str(in_srctree))
    with zipfile.ZipFile(in_srctree / whl) as zf:
        txt = zf.read("example_proj-0.1.dist-info/METADATA").decode()
    assert txt.rstrip() == expected_metadata.rstrip()


in_bytes = b"""\
Metadata-Version: 2.1
Name: foo
Platform: UNKNOWN
Version: 1.0

"""


expected_out_bytes = b"""\
Metadata-Version: 2.1
Name: foo
Version: 1.0

"""


def test_drop_unknown():
    out_bytes = setuptools_ext.rewrite_metadata(in_bytes, {})
    assert out_bytes == expected_out_bytes


def test_wheel_generator(in_srctree, monkeypatch):
    monkeypatch.setattr("setuptools_ext.version", lambda distribution_name: "0.1")
    in_srctree.joinpath("pyproject.toml").write_text(pyproject_full, encoding="utf8")
    whl = setuptools_ext.build_wheel(wheel_directory=str(in_srctree))
    with zipfile.ZipFile(in_srctree / whl) as zf:
        txt = zf.read("example_proj-0.1.dist-info/WHEEL").decode()
    [line] = [x for x in txt.splitlines() if x.startswith("Generator: ")]
    assert line.endswith(" + setuptools-ext (0.1)")


# For some reason the Requires-Dist looks different for sdist build vs wheel build.
# The requirement meaning is the same, but one or the other has been normalized.
expected_pkginfo = """\
Metadata-Version: 2.1
Name: example-proj
Version: 0.1
Summary: example summary
Author: Wim Glenn
Author-email: hey@wimglenn.com
License: MIT
Project-URL: homepage, https://example.org/
Description-Content-Type: text/x-rst
Provides-Extra: all
Requires-Dist: typing-extensions<5,>=4.2; python_version < "3.8" and extra == "all"
Requires-External: C
Requires-External: libpng (>=1.5)
Requires-External: make; sys_platform != "win32"
Supported-Platform: RedHat 8.3

this is the first line of the README.rst file
this is the second line of the README.rst file — and it has non-ascii in it
"""


def test_sdist(in_srctree):
    in_srctree.joinpath("pyproject.toml").write_text(pyproject_full, encoding="utf8")
    sdist_fname = setuptools_ext.build_sdist(sdist_directory=str(in_srctree))
    r = 0
    with tarfile.open(in_srctree / sdist_fname) as tf:
        for tarinfo in tf.getmembers():
            if tarinfo.name.endswith("/PKG-INFO"):
                content = tf.extractfile(tarinfo).read()
                assert content.decode() == expected_pkginfo
                r += 1
    # The sdists currently produced by setuptools have a PKG-INFO file both at root
    # and within an egg-info subdirectory. I don't know why, seems like historical
    # cruft or just a bug.
    assert r == 1 or r == 2
