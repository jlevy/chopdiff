from __future__ import annotations

import argparse
import sys
import tarfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

_REPOSITORY_ONLY_DIRS = frozenset(
    {".agents", ".claude", ".github", ".tbd", "docs", "examples", "tests"}
)


class SdistValidationError(ValueError):
    """The source distribution is missing, unreadable, or has an invalid manifest."""


def find_sdist(dist_dir: Path) -> Path:
    """Return the sole source archive in `dist_dir`."""
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(sdists) != 1:
        raise SdistValidationError(
            f"expected exactly one source archive in {dist_dir}, found {len(sdists)}"
        )
    return sdists[0]


def validate_sdist(sdist: Path) -> None:
    """Fail if `sdist` is unreadable or contains repository-only directories."""
    try:
        with tarfile.open(sdist, mode="r:gz") as archive:
            forbidden_dirs = sorted(
                {
                    part
                    for member in archive.getmembers()
                    for part in PurePosixPath(member.name).parts
                    if part in _REPOSITORY_ONLY_DIRS
                }
            )
    except (OSError, tarfile.TarError) as error:
        raise SdistValidationError(f"cannot read {sdist}: {error}") from error

    if forbidden_dirs:
        names = ", ".join(forbidden_dirs)
        raise SdistValidationError(f"{sdist} contains repository-only directories: {names}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a built source distribution.")
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)

    try:
        sdist = find_sdist(args.dist_dir)
        validate_sdist(sdist)
    except SdistValidationError as error:
        print(f"Source distribution validation failed: {error}", file=sys.stderr)
        return 1

    print(f"Source distribution manifest is valid: {sdist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
