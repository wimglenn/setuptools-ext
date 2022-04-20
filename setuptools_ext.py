"""Extension of setuptools to support all core metadata fields"""
__version__ = "0.1"

import base64
import email
import hashlib
from pathlib import Path
from zipfile import ZipFile

import setuptools.build_meta
try:
    # stdlib Python 3.11+
    import tomllib as toml
except ImportError:
    import toml

allowed_fields = [
    "Platform",
    "Supported-Platform",
    "Download-URL",
    "Requires-External",
    "Provides-Dist",
    "Obsoletes-Dist",
]

get_requires_for_build_sdist = setuptools.build_meta.get_requires_for_build_sdist
get_requires_for_build_wheel = setuptools.build_meta.get_requires_for_build_wheel
prepare_metadata_for_build_wheel = setuptools.build_meta.prepare_metadata_for_build_wheel


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    project = toml.loads(Path("pyproject.toml").read_text())
    ours = project.get("tool", {}).get("setuptools-ext", {})
    extra_metadata = {}
    for field in allowed_fields:
        val = ours.pop(field.lower(), None)
        if val:
            extra_metadata[field] = val
    for key, val in ours.items():
        print(f"WARNING: ignored an unsupported option {key} = {val}")
    whl = setuptools.build_meta.build_wheel(wheel_directory, config_settings, metadata_directory)
    if extra_metadata:
        rewrite_whl(Path(wheel_directory) / whl, extra_metadata)
    return whl


def build_sdist(sdist_directory, config_settings=None):
    tar_gz = setuptools.build_meta.build_sdist(sdist_directory, config_settings)
    return tar_gz


def rewrite_metadata(data, extra_metadata):
    pkginfo = email.message_from_bytes(data)
    if pkginfo.get_all("Platform") == ["UNKNOWN"]:
        # delete this annoying kv that distutils seems to put in there for no reason
        del pkginfo["Platform"]
    if pkginfo["License"] == "UNKNOWN":
        del pkginfo["License"]
    for key, vals in extra_metadata.items():
        already_present = pkginfo.get_all(key, [])
        for val in vals:
            if val not in already_present:
                pkginfo.add_header(key, val)
    return pkginfo.as_bytes()


def rewrite_record(data, new_record):
    lines = []
    for line in data.decode().splitlines():
        fname = line.split(",")[0]
        if fname.endswith(".dist-info/METADATA"):
            line = new_record
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
    with ZipFile(path, "r") as z_in, ZipFile(tmppath, "w") as z_out:
        z_out.comment = z_in.comment
        for zinfo in z_in.infolist():
            data = z_in.read(zinfo.filename)
            if zinfo.filename.endswith(".dist-info/METADATA"):
                data = rewrite_metadata(data, extra_metadata)
                checksum = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
                new_record = "{},sha256={},{}".format(zinfo.filename, checksum.decode(), len(data))
            if zinfo.filename.endswith(".dist-info/RECORD"):
                record = zinfo, data
                continue
            z_out.writestr(zinfo, data)
        if record is not None:
            record_info, record_data = record
            if checksum is not None:
                record_data = rewrite_record(record_data, new_record)
            z_out.writestr(record_info, record_data)
    path.write_bytes(tmppath.read_bytes())
    tmppath.unlink()


def rewrite_sdist(path, extra_metadata):
    # TODO: find out why there are two different PKG-INFO file in the .tar.gz ?!
    pass
