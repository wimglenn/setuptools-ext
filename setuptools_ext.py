"""Extension of setuptools to support all core metadata fields"""
from __future__ import unicode_literals

import base64
import email
import hashlib
import sys
from zipfile import ZipFile
from setuptools.build_meta import build_wheel as orig_build_wheel
from setuptools.build_meta import *

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
try:
    # stdlib Python 3.11+
    import tomllib as toml
except ImportError:
    import toml


__version__ = "0.4"


PY2 = sys.version_info < (3,)


allowed_fields = {
    x.lower(): x
    for x in [
        "Platform",
        "Supported-Platform",
        "Download-URL",
        "Requires-External",
        "Provides-Dist",
        "Obsoletes-Dist",
    ]
}


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    project = toml.loads(Path("pyproject.toml").read_text())
    ours = project.get("tool", {}).get("setuptools-ext", {})
    extra_metadata = {}
    for key, vals in ours.items():
        try:
            header = allowed_fields[key.lower()]
        except KeyError:
            print("WARNING: ignored an unsupported option {} = {}".format(key, vals))
            continue
        if not isinstance(vals, list):
            t = type(vals).__name__
            print("WARNING: coercing the value of {} from {} to list".format(key, t))
            vals = [vals]
        extra_metadata[header] = vals
    whl = orig_build_wheel(wheel_directory, config_settings, metadata_directory)
    if extra_metadata:
        rewrite_whl(Path(wheel_directory) / whl, extra_metadata)
    return whl


def rewrite_metadata(data, extra_metadata):
    pkginfo = email.message_from_string(data.decode())
    # delete some annoying kv that distutils seems to put in there for no reason
    for key in dict(pkginfo):
        if pkginfo.get_all(key) == ["UNKNOWN"]:
            if key.lower() not in ["metadata-version", "name", "version"]:
                del pkginfo[key]
    # dodge https://github.com/pypa/warehouse/issues/11220
    homepage = pkginfo.get("Home-page")
    if homepage is not None:
        if "homepage, {}".format(homepage) in pkginfo.get_all("Project-URL", []):
            del pkginfo["Home-page"]
    new_headers = extra_metadata.items()
    if PY2:
        new_headers.sort()
    for key, vals in sorted(extra_metadata.items()):
        already_present = pkginfo.get_all(key, [])
        for val in vals:
            if val not in already_present:
                pkginfo.add_header(key, val)
    result = pkginfo.as_string() if PY2 else pkginfo.as_bytes()
    return result


def rewrite_record(data, new_line):
    lines = []
    for line in data.decode().splitlines():
        fname = line.split(",")[0]
        if fname.endswith(".dist-info/METADATA"):
            line = new_line
        lines.append(line)
    return "\n".join(lines).encode()


def rewrite_whl(path, extra_metadata):
    """Add extra fields into the wheel's METADATA file"""
    # It would be a lot simpler if we could have just dropped the additional fields
    # into the dist-info as part of the `prepare_metadata_for_build_wheel` hook.
    # however, setuptools ignores this .dist-info directory when building the
    # wheel, and regenerates the metadata again:
    # https://github.com/pypa/setuptools/blob/v62.1.0/setuptools/build_meta.py#L241-L245
    # that's potentially a setuptools bug (seems like a PEP 517 violation), so it might
    # be changed later on, but unfortunately for now the only option is to rewrite the
    # generated .whl with our modifications
    tmppath = path.parent.joinpath("." + path.name)
    checksum = record = None
    with ZipFile(str(path), "r") as z_in, ZipFile(str(tmppath), "w") as z_out:
        z_out.comment = z_in.comment
        for zinfo in z_in.infolist():
            data = z_in.read(zinfo.filename)
            if zinfo.filename.endswith(".dist-info/METADATA"):
                data = rewrite_metadata(data, extra_metadata)
                digest = hashlib.sha256(data).digest()
                checksum = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
                new_line = "{},sha256={},{}".format(zinfo.filename, checksum, len(data))
            if zinfo.filename.endswith(".dist-info/RECORD"):
                record = zinfo, data
                continue
            z_out.writestr(zinfo, data)
        if record is not None:
            record_info, record_data = record
            if checksum is not None:
                record_data = rewrite_record(record_data, new_line)
            z_out.writestr(record_info, record_data)
    path.write_bytes(tmppath.read_bytes())
    tmppath.unlink()
