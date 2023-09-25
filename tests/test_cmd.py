# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from click.testing import CliRunner
import responses

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
