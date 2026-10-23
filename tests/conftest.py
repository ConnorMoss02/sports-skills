"""Pytest collection policy for immutable historical release proofs."""

import os
from pathlib import Path

HISTORICAL_RELEASE_TESTS = {
    "test_release_036.py": "SPORTS_SKILLS_VERIFY_RELEASE_036",
    "test_release_037.py": "SPORTS_SKILLS_VERIFY_RELEASE_037",
}


def pytest_ignore_collect(collection_path, config):
    """Keep the v0.36 and v0.37 proofs opt-in after those immutable releases.

    The historical checksum tests rebuild the current source tree, so any later
    feature correctly changes their artifacts. Release verification can enable a
    frozen proof explicitly without disabling pytest's other ignore hooks.
    """
    path = Path(str(collection_path))
    variable = HISTORICAL_RELEASE_TESTS.get(path.name)
    if variable is None:
        return None
    return os.environ.get(variable) != "1"
