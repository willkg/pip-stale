#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
from packaging.version import parse as version_parse, InvalidVersion
import pathlib
import re
import subprocess

import click
import requests
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


def check_versions(name, version):
    """Given a package name and version, returns a VersionInfo

    :arg name: package name
    :arg version: currently used version

    :returns: VersionInfo

    """
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


def parse_and_check(package_specs):
    """Take a set of "pkg" or "pkg==X.Y.Z" lines and return version info

    :arg package_specs: list of "pkg" or "pkg==X.Y.Z" strings

    :returns: generator of VersionInfo instances

    """
    continued_line = ""
    for line in package_specs:
        if "#" in line:
            line = line[: line.find("#")]

        if not line.strip():
            continue

        if line.strip().endswith("\\"):
            continued_line = continued_line + line.strip().rstrip("\\")
            continue

        if continued_line:
            line = continued_line + " " + line.strip().rstrip("\\")
            continued_line = ""

        parts = line.split(" ")
        if parts[0].startswith("-"):
            print(f"Skipping line {line!r}...")
            continue

        if "==" in parts[0]:
            name, version = parts[0].split("==")
        else:
            name, version = parts[0], NO_VERSION

        if ";" in version:
            version = version[0 : version.find(";")]

        if "[" in name:
            name = name[: name.find("[")]

        yield check_versions(name, version)


@click.command()
@click.option("--requirements", help="Requirements file.", multiple=True)
@click.option("--env", default=False, is_flag=True, help="This environment.")
@click.option(
    "--error-if-updates/--no-error-if-updates",
    default=False,
    help="Exit with 1 if there are updates available.",
)
@click.argument("pkg", nargs=-1)
@click.pass_context
def main(ctx, requirements, env, error_if_updates, pkg):
    """Determine stale requirements and upgrade options.

     This works on packages passed in via the command line:

        pip-stale django

        pip-stale django==3.2.0

    This works on requirements files:

        pip-stale --requirements=requirements.in

    This works on environments and virtual environments:

        pip-stale --env

    """
    console = Console()

    things = []
    if pkg:
        things.extend(pkg)

    if requirements:
        for req_file in requirements:
            path = pathlib.Path(req_file).resolve().absolute()

            if not path.exists():
                console.print(f"[yellow]Path {path} does not exist.[/yellow]")
                ctx.exit(1)

            things.extend(path.read_text().splitlines())

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

    updated_version_info = [
        version_info
        for version_info in parse_and_check(things)
        if version_info.has_update() or version_info.error
    ]

    if not updated_version_info:
        return

    # FIXME(willkg): offer other formats
    table = Table(show_edge=False, show_header=True)
    table.add_column("name")
    table.add_column("current version")
    table.add_column("latest")
    table.add_column("latest minor")
    table.add_column("latest patch")

    def version_or_blank(version):
        return version if version != NO_VERSION else ""

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
                version_or_blank(version_info.version),
                version_info.error,
            )
            continue

        table.add_row(
            version_info.name,
            version_or_blank(version_info.version),
            colorize(version_info.version, version_info.latest),
            colorize(version_or_blank(version_info.version), version_info.minor),
            colorize(version_or_blank(version_info.version), version_info.patch),
        )

    console.print(table)

    if error_if_updates:
        ctx.exit(1)


if __name__ == "__main__":
    main()
