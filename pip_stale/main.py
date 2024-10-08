#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import csv
from dataclasses import dataclass
import io
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import parse as version_parse, InvalidVersion
import pathlib
import re
import subprocess

import click
import requests
from rich import box
from rich.console import Console
from rich.table import Table


class NotFound(Exception):
    pass


class UnknownError(Exception):
    pass


# NOTE(willkg): This works, but goes against the TUF section in the spec.
PYPI_SIMPLE_API = "https://pypi.org/simple"


def get_package_info(package):
    # Use the simple API. https://peps.python.org/pep-0691/
    headers = {
        "User-Agent": "pip-stale",
        "Accept": "application/vnd.pypi.simple.v1+json",
    }
    url = f"{PYPI_SIMPLE_API}/{package}/"
    resp = requests.get(url, headers=headers, allow_redirects=True, timeout=5.0)

    if resp.status_code == 200:
        return resp.json()

    elif resp.status_code == 404:
        raise NotFound(f"Package {package!r} not found")

    raise UnknownError(
        f"Unknown error for retrieving package data {package!r} {resp.status_code}"
    )


NO_VERSION = "0.0.0"


@dataclass
class VersionInfo:
    name: str
    version: str
    latest: str = None
    minor: str = None
    patch: str = None
    error: str = None

    def has_update(self):
        return not (self.version == self.latest == self.minor == self.patch)


def check_versions(req):
    """Given a package name and version, returns a VersionInfo

    :arg req: a Requirement instance

    :returns: VersionInfo

    """
    name = req.name
    # FIXME(willkg): we're only going to look at the first specifier; if
    # we need to support multiple specifiers, we'll have to figure out what to do
    version = sorted(req.specifier)[0].version

    parsed_version = version_parse(version)
    parsed_version_minor = parsed_version.major
    parsed_version_patch = (parsed_version.major, parsed_version.minor)

    try:
        data = get_package_info(name)
    except NotFound:
        return VersionInfo(
            name=name,
            version=version,
            latest=None,
            minor=None,
            patch=None,
            error="Not found",
        )
    except UnknownError:
        return VersionInfo(
            name=name,
            version=version,
            latest=None,
            minor=None,
            patch=None,
            error="Unknown error",
        )

    # None or a (Version, version string)
    latest_version = None
    latest_minor = None
    latest_patch = None

    for release_version in data["versions"]:
        try:
            parsed_release_version = version_parse(release_version)
        except InvalidVersion:
            continue

        if parsed_release_version.is_prerelease and not parsed_version.is_prerelease:
            # Skip pre-releases unless the package is curently using a
            # pre-release version
            continue

        if parsed_release_version < parsed_version:
            continue

        minor = parsed_release_version.major
        if minor == parsed_version_minor and (
            latest_minor is None or parsed_release_version > latest_minor[0]
        ):
            latest_minor = (parsed_release_version, release_version)

        patch = (parsed_release_version.major, parsed_release_version.minor)
        if patch == parsed_version_patch and (
            latest_patch is None or parsed_release_version > latest_patch[0]
        ):
            latest_patch = (parsed_release_version, release_version)

        if parsed_release_version >= parsed_version and (
            latest_version is None or parsed_release_version > latest_version[0]
        ):
            latest_version = (parsed_release_version, release_version)

    if version == NO_VERSION:
        return VersionInfo(
            name=name,
            version=version,
            latest=latest_version[1],
            minor=latest_version[1],
            patch=latest_version[1],
            error=None,
        )

    return VersionInfo(
        name=name,
        version=version,
        latest=latest_version and latest_version[1],
        minor=latest_minor and latest_minor[1],
        patch=latest_patch and latest_patch[1],
        error=None,
    )


def parse_requirements(requirements, console, verbose=False):
    """Take a list of "pkg" or "pkg==X.Y.Z" lines and returns Requirements

    :arg requirements: list of "pkg" or "pkg==X.Y.Z" strings; or the lines
        from a requirements file
    arg console: a console to print to
    :arg verbose: whether or not to print verbose output

    :returns: generator of Requirement instances

    """
    continued_line = ""
    for line in requirements:
        if "#" in line:
            line = line[: line.find("#")]

        if not line.strip():
            continue

        if line.strip().endswith("\\"):
            if not line.strip().startswith("--hash"):
                continued_line = continued_line + line.strip().rstrip("\\")
            continue

        if continued_line:
            if not line.strip().startswith("--hash"):
                line = continued_line + " " + line.strip().rstrip("\\")
            else:
                line = continued_line
            continued_line = ""

        # Skip over -e and -r lines
        if line.startswith("-"):
            if verbose:
                console.print(f"Skipping line {line!r}...", highlight=False)
            continue

        req = Requirement(requirement_string=line)
        if len(req.specifier) == 0:
            req.specifier = req.specifier & SpecifierSet("==0.0.0")

        yield req


@click.command(name="pip-stale")
@click.option("--env", default=False, is_flag=True, help="This environment.")
@click.option(
    "--show",
    "show_versions_value",
    default="latest,minor,patch",
    help="Comma-separated list of versions to show.",
)
@click.option(
    "--format",
    "format_type",
    default="table",
    show_default=True,
    type=click.Choice(["table", "csv"], case_sensitive=False),
    help="Format to print output.",
)
@click.option(
    "--error-if-updates/--no-error-if-updates",
    default=False,
    help="Exit with 1 if there are updates available.",
)
@click.option(
    "--verbose/--no-verbose",
    default=False,
    help="Whether to print verbose output.",
)
@click.argument("pkg_or_file", nargs=-1)
@click.pass_context
def pip_stale_main(
    ctx, env, show_versions_value, format_type, error_if_updates, verbose, pkg_or_file
):
    """Determine stale requirements and upgrade options.

     This works on packages passed in via the command line:

        pip-stale django

        pip-stale django==3.2.0

    This works on requirements files:

        pip-stale requirements.in

        pip-stale requirements/*.txt

    This works on environments and virtual environments:

        pip-stale --env

    """
    console = Console()

    show_versions = [item.strip() for item in show_versions_value.split(",")]
    for item in show_versions:
        if item not in ["latest", "minor", "patch"]:
            console.print(
                f"{item!r} from {show_versions_value!r} is not valid. "
                + "Must be a comma-separated list of 'latest', 'minor', and 'patch'"
            )
            ctx.exit(1)

    things = []
    if pkg_or_file:
        for item in pkg_or_file:
            item = item.strip()
            path = pathlib.Path(item).resolve().absolute()
            if path.exists():
                things.extend(path.read_text().splitlines())
            elif "==" in item:
                things.append(item)
            else:
                try:
                    get_package_info(item)
                    things.append(item)
                except (NotFound, UnknownError):
                    console.print(
                        f"[yellow]Path or package {item} does not exist.[/yellow]"
                    )
                    ctx.exit(1)

    if env:
        # The things pip does to get the list of things installed is tough, so
        # we're just going to use pip.
        ret = subprocess.run(
            [
                "pip",
                "list",
                "--no-input",
                "--no-color",
                "--no-python-version-warning",
            ],
            capture_output=True,
        )
        if ret.returncode != 0:
            console.print("[yellow]'pip list' returned error[/yellow]")
            ctx.exit(1)
        output = ret.stdout.decode("utf-8").splitlines()[2:]
        lines = [re.sub(r"\s+", "==", line.strip()) for line in output]
        things.extend(lines)

    updated_version_info = []
    for req in parse_requirements(things, console=console, verbose=verbose):
        version_info = check_versions(req)
        if version_info.has_update() or version_info.error:
            updated_version_info.append(version_info)
        elif verbose:
            console.print(
                f"{version_info.name} at {version_info.version} is up-to-date.",
                highlight=False,
            )

    if not updated_version_info:
        if verbose:
            console.print("All requirements up-to-date.")
        return

    if format_type == "table":
        # FIXME(willkg): offer other formats
        table = Table(show_edge=False, show_header=True, box=box.MARKDOWN)
        table.add_column("name")
        table.add_column("current version")
        if "latest" in show_versions:
            table.add_column("latest")
        if "minor" in show_versions:
            table.add_column("latest minor")
        if "patch" in show_versions:
            table.add_column("latest patch")

        def colorize(version, new_version):
            if not version:
                return

            if version == new_version:
                return new_version
            else:
                return f"[green]{new_version}[/green]"

        for version_info in updated_version_info:
            if version_info.error:
                table.add_row(
                    version_info.name,
                    version_info.version,
                    version_info.error,
                )
                continue

            row = [version_info.name, version_info.version]
            if "latest" in show_versions:
                row.append(colorize(version_info.version, version_info.latest))
            if "minor" in show_versions:
                row.append(colorize(version_info.version, version_info.minor))
            if "patch" in show_versions:
                row.append(colorize(version_info.version, version_info.patch))
            table.add_row(*row)

        console.print(table)

    elif format_type == "csv":
        buffer = io.StringIO()
        csvwriter = csv.writer(buffer)
        headers = ["name", "current version"]
        if "latest" in show_versions:
            headers.append("latest")
        if "minor" in show_versions:
            headers.append("latest minor")
        if "patch" in show_versions:
            headers.append("latest patch")
        csvwriter.writerow(headers)
        for version_info in updated_version_info:
            if version_info.error:
                csvwriter.writerow(
                    [version_info.name, version_info.version, version_info.error]
                )
                continue

            row = [version_info.name, version_info.version]
            if "latest" in show_versions:
                row.append(version_info.latest)
            if "minor" in show_versions:
                row.append(version_info.minor)
            if "patch" in show_versions:
                row.append(version_info.patch)
            csvwriter.writerow(row)

        for line in buffer.getvalue().splitlines():
            console.print(line, highlight=False)

    if error_if_updates:
        ctx.exit(1)


if __name__ == "__main__":
    pip_stale_main()
