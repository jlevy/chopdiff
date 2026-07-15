from __future__ import annotations

import tarfile
from contextlib import redirect_stderr
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from devtools.validate_sdist import SdistValidationError, find_sdist, main, validate_sdist

_REPO_ROOT = Path(__file__).parent.parent
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"


def _write_sdist(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, mode="w:gz") as archive:
        for name, contents in members.items():
            member = tarfile.TarInfo(name)
            member.size = len(contents)
            archive.addfile(member, BytesIO(contents))


def test_invalid_source_archive_is_rejected() -> None:
    with TemporaryDirectory() as temp_dir:
        sdist = Path(temp_dir) / "chopdiff-1.0.0.tar.gz"
        sdist.write_text("not a tar archive")

        try:
            validate_sdist(sdist)
        except SdistValidationError:
            return

        raise AssertionError("invalid source archive was accepted")


def test_repository_only_directory_is_rejected() -> None:
    with TemporaryDirectory() as temp_dir:
        sdist = Path(temp_dir) / "chopdiff-1.0.0.tar.gz"
        _write_sdist(sdist, {"chopdiff-1.0.0/.github/workflows/ci.yml": b"name: CI"})

        try:
            validate_sdist(sdist)
        except SdistValidationError as error:
            assert ".github" in str(error)
            return

        raise AssertionError("repository-only directory was accepted")


def test_missing_source_archive_is_rejected() -> None:
    with TemporaryDirectory() as temp_dir:
        try:
            find_sdist(Path(temp_dir))
        except SdistValidationError as error:
            assert "found 0" in str(error)
            return

        raise AssertionError("missing source archive was accepted")


def test_command_fails_when_source_archive_is_missing() -> None:
    with TemporaryDirectory() as temp_dir:
        stderr = StringIO()
        with redirect_stderr(stderr):
            exit_code = main([temp_dir])

        assert exit_code == 1
        assert "found 0" in stderr.getvalue()


def test_release_workflows_validate_sdist_before_using_artifacts() -> None:
    artifact_consumers = {
        "ci.yml": "uv pip install",
        "publish.yml": "uv publish",
    }
    validation_command = "uv run --locked python devtools/validate_sdist.py"

    for workflow_name, artifact_consumer in artifact_consumers.items():
        workflow = (_WORKFLOWS / workflow_name).read_text()
        assert validation_command in workflow
        assert workflow.index("uv build --no-sources") < workflow.index(validation_command)
        assert workflow.index(validation_command) < workflow.index(artifact_consumer)
