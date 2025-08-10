"""Tests verifying that progress bar output stays silent during non-verbose runs."""

import os
import pytest


def test_tqdm_disabled_by_default(pytestconfig):
    """TQDM progress bars should be disabled when pytest runs quietly.

    The fixture in ``conftest`` sets ``TQDM_DISABLE`` for default test runs, so
    the simulation and optimisation routines execute without emitting noisy
    progress bars. If a developer wants to inspect progress they can re-run the
    suite with ``-v`` to keep the bars enabled.
    """

    if pytestconfig.getoption("verbose") > 0:
        pytest.skip("Progress bars are expected when verbosity is requested.")
    assert os.environ.get("TQDM_DISABLE") == "1"
