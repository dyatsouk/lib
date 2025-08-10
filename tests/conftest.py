"""Pytest configuration used across the test suite.

This module ensures that progress bars from :mod:`tqdm` do not clutter
standard test runs. The progress output is useful when debugging but
normally hides failures, so we silence it unless the user explicitly asks
for verbose output with ``-v``.
"""

from __future__ import annotations

import os
import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Run before tests are collected to adjust global test behaviour.

    The ``TQDM_DISABLE`` environment variable tells :mod:`tqdm` to return a
    plain iterable without emitting a progress bar. Setting it here ensures it
    is in place before any project modules import :mod:`tqdm` during test
    collection. When pytest runs with its default verbosity (or with ``-q``),
    we set the variable so progress output stays silent. Passing ``-v`` leaves
    progress bars enabled for developers who want extra insight.
    """

    if config.getoption("verbose") <= 0:
        # Configure the environment early so every progress bar instantiated by
        # the code under test remains silent throughout the run.
        os.environ.setdefault("TQDM_DISABLE", "1")
