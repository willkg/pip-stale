# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Generates test HTTP responses.
"""

import requests
from responses import _recorder


@_recorder.record(file_path="tests/pypi_output.yaml")
def populate_test_output():
    headers = {
        "User-Agent": "pip-stale-tests",
        "Accept": "application/vnd.pypi.simple.v1+json",
    }
    # This exists in PyPI
    requests.get("https://pypi.org/simple/markus/", headers=headers)
    # This doesn't exist in PyPI
    requests.get("https://pypi.org/simple/nonexistent-package/", headers=headers)


if __name__ == "__main__":
    populate_test_output()
