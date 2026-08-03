import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trajectory as _traj  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--run-dir",
        action="store",
        default=os.environ.get("ERZA_RUN_DIR", ""),
        help="Erza run directory containing trajectory/llm_trajectory.jsonl",
    )


@pytest.fixture(scope="session")
def traj(request):
    run_dir = request.config.getoption("--run-dir")
    if not run_dir:
        pytest.fail("no --run-dir given (or ERZA_RUN_DIR unset)")
    if not os.path.isdir(run_dir):
        pytest.fail(f"run dir does not exist: {run_dir}")
    return _traj.load(run_dir)
