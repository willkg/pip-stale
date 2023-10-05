# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import textwrap

from click.testing import CliRunner
import pytest
import responses
from rich.console import Console

from pip_stale import main


@responses.activate
def test_it_runs():
    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--help"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0


@responses.activate
def test_package_no_version():
    responses.patch("https://pypi.org/simple/markus/")
    responses._add_from_file(file_path="tests/pypi_output.yaml")

    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--format=csv", "markus"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0
    assert result.output == textwrap.dedent(
        """\
        name,current version,latest,latest minor,latest patch
        markus,0.0.0,4.2.0,4.2.0,4.2.0
        """
    )


@responses.activate
def test_package_version():
    responses.patch("https://pypi.org/simple/markus/")
    responses._add_from_file(file_path="tests/pypi_output.yaml")

    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--format=csv", "markus==2.0.0"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0
    assert result.output == textwrap.dedent(
        """\
        name,current version,latest,latest minor,latest patch
        markus,2.0.0,4.2.0,2.2.0,2.0.0
        """
    )


@responses.activate
def test_package_doesnt_exist():
    responses.patch("https://pypi.org/simple/nonexistent-package/")
    responses._add_from_file(file_path="tests/pypi_output.yaml")

    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--format=csv", "nonexistent-package"],
        env={"COLUMNS": "100"},
    )
    print(result.output)
    assert result.exit_code == 1
    assert result.output == "Path or package nonexistent-package does not exist.\n"


@responses.activate
def test_requirements():
    responses.patch("https://pypi.org/simple/markus/")
    responses._add_from_file(file_path="tests/pypi_output.yaml")

    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--format=csv", "tests/requirements.txt"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0
    assert result.output == textwrap.dedent(
        """\
        name,current version,latest,latest minor,latest patch
        markus,2.0.0,4.2.0,2.2.0,2.0.0
        nonexistent-package,1.0.0,Not found
        """
    )


@pytest.mark.parametrize(
    "showvalue, expected",
    [
        (
            "latest",
            textwrap.dedent(
                """\
                name,current version,latest
                markus,2.0.0,4.2.0
                """
            ),
        ),
        (
            "minor",
            textwrap.dedent(
                """\
                name,current version,latest minor
                markus,2.0.0,2.2.0
                """
            ),
        ),
        (
            "patch",
            textwrap.dedent(
                """\
                name,current version,latest patch
                markus,2.0.0,2.0.0
                """
            ),
        ),
        (
            "latest,minor",
            textwrap.dedent(
                """\
                name,current version,latest,latest minor
                markus,2.0.0,4.2.0,2.2.0
                """
            ),
        ),
    ],
)
@responses.activate
def test_package_show(showvalue, expected):
    responses.patch("https://pypi.org/simple/markus/")
    responses._add_from_file(file_path="tests/pypi_output.yaml")

    runner = CliRunner()
    result = runner.invoke(
        cli=main.pip_stale_main,
        args=["--format=csv", f"--show={showvalue}", "markus==2.0.0"],
        env={"COLUMNS": "100"},
    )
    assert result.exit_code == 0
    assert result.output == expected


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
