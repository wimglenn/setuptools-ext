"""Extension of setuptools to support all core metadata fields"""

import base64
import email.policy
import hashlib
import shutil
import sys
import typing
import zipfile
from pathlib import Path

from setuptools.build_meta import *  # noqa
from setuptools.build_meta import build_wheel as orig_build_wheel

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


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
    project = tomllib.loads(Path("pyproject.toml").read_text())
    ours = project.get("tool", {}).get("setuptools-ext", {})
    extra_metadata = {}
    for key, vals in ours.items():
        try:
            header = allowed_fields[key.lower()]
        except KeyError:
            print(f"WARNING: ignored an unsupported option {key} = {vals}")
            continue
        if not isinstance(vals, list):
            t = type(vals).__name__
            print(f"WARNING: coercing the value of {key} from {t} to list")
            vals = [vals]
        extra_metadata[header] = vals
    whl = orig_build_wheel(wheel_directory, config_settings, metadata_directory)
    if extra_metadata:
        rewrite_whl(Path(wheel_directory) / whl, extra_metadata)
    return whl


def rewrite_metadata(data, extra_metadata):
    """
    Rewrite the METADATA file to include the given additional metadata.
    """
    pkginfo = email.message_from_string(data.decode())
    # delete some annoying kv that distutils seems to put in there for no reason
    for key in dict(pkginfo):
        if pkginfo.get_all(key) == ["UNKNOWN"]:
            if key.lower() not in ["metadata-version", "name", "version"]:
                del pkginfo[key]
    new_headers = extra_metadata.items()
    for key, vals in new_headers:
        already_present = pkginfo.get_all(key, [])
        for val in vals:
            if val not in already_present:
                pkginfo.add_header(key, val)
    policy = email.policy.Compat32(max_line_length=0)
    result = pkginfo.as_bytes(policy=policy)
    return result


class WheelRecord:
    """
    Represents the RECORD file of a wheel, which can be updated with new checksums
    using the record_file method.

    See also the (limited) spec on RECORD at
    https://packaging.python.org/en/latest/specifications/binary-distribution-format/#signed-wheel-files
    """

    def __init__(self, record_content: str = ""):
        #: Records mapping filename to (hash, length) tuples.
        self._records: typing.Dict[str, typing.Tuple[str, str]] = {}
        self.update_from_record(record_content)

    def update_from_record(
        self, record_content: typing.Union[str, "WheelRecord"]
    ) -> None:
        """
        Update this WheelRecord given another WheelRecord, or RECORD contents
        """
        if isinstance(record_content, WheelRecord):
            record_content = record_content.record_contents()
        for line in record_content.splitlines():
            path, file_hash, length = line.split(",")
            self._records[path] = file_hash, length

    def record_file(self, filename, file_content: typing.Union[bytes, str]):
        """
        Record the filename and appropriate digests of its contents
        """
        if isinstance(file_content, str):
            file_content = file_content.encode("utf-8")
        digest = hashlib.sha256(file_content).digest()
        checksum = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        self._records[filename] = f"sha256={checksum}", str(len(file_content))

    def record_contents(self) -> str:
        """
        Output the representation of this WheelRecord as a string, suitable for
        writing to a RECORD file.
        """
        contents = []
        for path, (file_hash, length) in self._records.items():
            contents.append(f"{path},{file_hash},{length}")
        return "\n".join(contents)


class WheelModifier:
    """
    Representation of an existing wheel with lazily modified contents that
    can be written on-demand with the write_wheel method.
    """

    def __init__(self, wheel_zipfile: zipfile.ZipFile):
        self._wheel_zipfile = wheel_zipfile
        # Track updated file contents.
        self._updates: typing.Dict[str, typing.Tuple[zipfile.ZipInfo, bytes]] = {}

    def dist_info_dirname(self):
        for filename in self._wheel_zipfile.namelist():
            # TODO: We could use the filename of the zipfile... but we don't
            #  necessarily have it.
            if filename.endswith(".dist-info/METADATA"):
                return filename.rsplit("/", 1)[0]

    def read(self, filename: str) -> bytes:
        if filename in self._updates:
            return self._updates[filename][1]
        else:
            return self._wheel_zipfile.read(filename)

    def zipinfo(self, filename: str) -> zipfile.ZipInfo:
        if filename in self._updates:
            return self._updates[filename][0]
        return self._wheel_zipfile.getinfo(filename)

    def write(
        self,
        filename: typing.Union[str, zipfile.ZipInfo],
        content: bytes,
    ) -> None:
        zinfo: zipfile.ZipInfo
        if isinstance(filename, zipfile.ZipInfo):
            zinfo = filename
        else:
            try:
                zinfo = self.zipinfo(filename)
            except KeyError:
                raise ValueError(
                    f"Unable to write filename {filename} as there is no existing "
                    "file information in the archive. Please provide a zipinfo "
                    "instance when writing."
                )
        self._updates[typing.cast(str, zinfo.filename)] = zinfo, content

    def write_wheel(self, file: typing.Union[str, Path, typing.IO[bytes]]) -> None:
        distinfo_dir = self.dist_info_dirname()
        record_filename = f"{distinfo_dir}/RECORD"
        orig_record = WheelRecord(self.read(record_filename).decode())
        with zipfile.ZipFile(file, "w") as z_out:
            for zinfo in self._wheel_zipfile.infolist():
                if zinfo.filename == record_filename:
                    # We deal with record last.
                    continue
                if zinfo.filename in self._updates:
                    zinfo, content = self._updates.pop(zinfo.filename)
                    orig_record.record_file(zinfo.filename, content)
                else:
                    content = self._wheel_zipfile.read(zinfo.filename)
                z_out.writestr(zinfo, content)
            for zinfo, content in self._updates.values():
                orig_record.record_file(zinfo.filename, content)
                z_out.writestr(zinfo, content)
            record_zinfo = self._wheel_zipfile.getinfo(record_filename)
            z_out.writestr(record_zinfo, orig_record.record_contents())


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

    with zipfile.ZipFile(str(path), "r") as whl_zip:
        whl = WheelModifier(whl_zip)
        metadata_filename = f"{whl.dist_info_dirname()}/METADATA"
        metadata = rewrite_metadata(whl.read(metadata_filename), extra_metadata)
        whl.write(metadata_filename, metadata)
        with tmppath.open("wb") as whl_fh:
            whl.write_wheel(whl_fh)

    shutil.move(tmppath, path)
