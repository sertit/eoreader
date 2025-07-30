from dataclasses import dataclass
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--ci_db_dir", type=Path, default=None, help="Override CI data base directory"
    )

    parser.addoption(
        "--tmp_directory",
        type=Path,
        default=None,
        help="Set to True to place every temporary data in the directory",
    )


@pytest.fixture(autouse=True)
def patch_ci_db_dir(request, monkeypatch):
    ci_db_dir = request.config.getoption("--ci_db_dir")
    if ci_db_dir:
        monkeypatch.setattr("ci.scripts_utils.get_ci_db_dir", lambda: Path(ci_db_dir))


@dataclass
class EOReaderTestsPath:
    tmpdir: Path


@pytest.fixture
def eoreader_tests_path(request):
    tmpdir_option = request.config.getoption("--tmp_directory")

    tmpdir = Path("/mnt/ds2_db3/CI/eoreader/OUTPUT")
    if tmpdir_option:
        tmpdir = Path(tmpdir_option)
    return EOReaderTestsPath(tmpdir=tmpdir)
