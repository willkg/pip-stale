# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from click.testing import CliRunner
import pytest
import responses
from rich.console import Console

from pip_stale import main


@responses.activate
def test_it_runs():
    runner = CliRunner()
    result = runner.invoke(
        cli=main.main,
        args=["--help"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "specs, expected",
    [
        (["tomli"], [("tomli", "==0.0.0")]),
        (["tomli==1.0.0"], [("tomli", "==1.0.0")]),
        # Handle comments correctly
        (
            [
                "# NOTE(willkg): we need this until we're Python > 3.7",
                "importlib_resources==6.1.0",
            ],
            [("importlib_resources", "==6.1.0")],
        ),
        # Handle blank lines
        (
            [
                "    ",
                "importlib_resources==6.1.0",
                "",
            ],
            [("importlib_resources", "==6.1.0")],
        ),
        # Handle environment markers (ignore them)
        (
            ["tomli>=2.0.1; python_version < '3.11'"],
            [("tomli", ">=2.0.1")],
        ),
        (
            ["black==23.9.1; implementation_name == 'cpython'"],
            [("black", "==23.9.1")],
        ),
    ],
)
def test_parse_and_check(specs, expected):
    console = Console()
    reqs = list(main.parse_requirements(specs, console=console))
    assert [(req.name, str(req.specifier)) for req in reqs] == expected
