import argparse
import dataclasses
import datetime
import os
import tarfile
import zipfile
from typing import Any, Dict


@dataclasses.dataclass(frozen=True)
class ManifestEntry:
    name: str
    size: int
    mtime: datetime.datetime
    original: Any


def compare_subset(a, b, keys) -> Dict[str, Any]:
    ret = {}
    for key in keys:
        va = getattr(a, key)
        vb = getattr(b, key)
        if va != vb:
            ret[key] = (va, vb)
    return ret


def read_tar_manifest(filename) -> Dict[str, ManifestEntry]:
    with tarfile.open(filename, "r") as tf:
        return {
            ti.name: ManifestEntry(
                name=ti.name,
                size=ti.size,
                mtime=datetime.datetime.fromtimestamp(ti.mtime),
                original=ti,
            )
            for ti in tf.getmembers()
            if not ti.isdir()
        }


def read_zip_manifest(filename) -> Dict[str, ManifestEntry]:
    with zipfile.ZipFile(filename, "r") as zf:
        return {
            info.filename: ManifestEntry(
                name=info.filename,
                size=info.file_size,
                mtime=datetime.datetime(*info.date_time),
                original=info,
            )
            for info in (zf.getinfo(name) for name in zf.namelist())
        }


def read_package_manifest(filename: str):
    ext = os.path.splitext(filename)[-1].lower()
    if ".tar." in filename or ext == ".tgz":
        return read_tar_manifest(filename)
    if ext in (".zip", ".whl"):
        return read_zip_manifest(filename)
    raise ValueError(f"No reader for {filename}")


def strip_if_possible(components, strip: int):
    return components[strip:] if len(components) > strip else components


def strip_names(manifest, strip: int):
    return {
        os.sep.join(strip_if_possible(key.split(os.sep), strip)): value
        for (key, value) in manifest.items()
    }


def diff_common(a, b):
    sa = set(a)
    sb = set(b)
    return (sa - sb, sb - sa, sa & sb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", metavar="FILE", nargs="+")
    ap.add_argument("--strip", type=int, default=0)
    ap.add_argument("--compare-mtime", action="store_true", default=False)
    args = ap.parse_args()
    if len(args.files) != 2:
        raise ValueError("Only 2 files are supported at this time.")
    f1, f2 = args.files
    m1 = strip_names(read_package_manifest(f1), strip=args.strip)
    m2 = strip_names(read_package_manifest(f2), strip=args.strip)

    only_in_1, only_in_2, common = diff_common(m1, m2)
    if only_in_1:
        print(f"# {len(only_in_1)} files only in {f1}")
        for filename in sorted(only_in_1):
            print(filename)
    if only_in_2:
        print(f"# {len(only_in_2)} files only in {f2}")
        for filename in sorted(only_in_2):
            print(filename)
    if common:
        print(f"# {len(common)} common files")
        comparison_keys = {"size"}
        if args.compare_mtime:
            comparison_keys.add("mtime")
        for filename in sorted(common):
            e1 = m1[filename]
            e2 = m2[filename]
            diffs = compare_subset(e1, e2, keys=comparison_keys)
            if diffs:
                print(filename, diffs)


if __name__ == "__main__":
    main()
