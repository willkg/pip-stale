=========
pip-stale
=========

pip-stale finds stale dependencies and most recent versions. It'll look at
requirements files, environments, virtual environments, and command line
specified packages.

:Code:          https://github.com/willkg/pip-stale
:Issues:        https://github.com/willkg/pip-stale/issues
:License:       MPL v2


Goals
=====

Goals of pip-stale:

1. works with command-line specified packages, ``requirements.in`` files, and
   the environment
2. tells you which dependencies are stale, latest version, latest minor
   version, and latest patch version--this helps with dependencies when you're
   using LTS or are locked into an older major version
3. straight-forward to use

pip-stale is inspired by `piprot <https://pypi.org/project/piprot/>`__.


Install and run
===============

This isn't on PyPI, yet, because I'm waffling on the name and whether there
needs to exist yet another dependency version checker.

For now, install like this::

    $ pipx install https://github.com/willkg/pip-stale/archive/refs/heads/main.zip

Examples::

    # Get version information for a specific package
    $ pip-stale markus
    $ pip-stale markus==2.0.0

    # Show just the latest version with CSV output
    $ pip-stale --format=csv --show=latest markus

    # Get version information for a requirements file
    $ pip-stale requirements.in

    # Get version information for packages installed in the environment
    $ pip-stale --env

.. [[[cog
   import cog
   import subprocess
   ret = subprocess.run(["pip-stale", "--help"], capture_output=True)
   cog.outl("\nHelp text::\n")
   cog.outl("   $ pip-stale --help")
   for line in ret.stdout.decode("utf-8").splitlines():
       if line.strip():
           cog.outl(f"   {line}")
       else:
           cog.outl("")
   cog.outl("")
   ]]]

Help text::

   $ pip-stale --help
   Usage: pip-stale [OPTIONS] [PKG_OR_FILE]...

     Determine stale requirements and upgrade options.

      This works on packages passed in via the command line:

         pip-stale django

         pip-stale django==3.2.0

     This works on requirements files:

         pip-stale requirements.in

         pip-stale requirements/*.txt

     This works on environments and virtual environments:

         pip-stale --env

   Options:
     --env                           This environment.
     --show TEXT                     Comma-separated list of versions to show.
     --format [table|csv]            Format to print output.  [default: table]
     --error-if-updates / --no-error-if-updates
                                     Exit with 1 if there are updates available.
     --verbose / --no-verbose        Whether to print verbose output.
     --help                          Show this message and exit.

.. [[[end]]]


Quick start
===========

.. [[[cog
   import cog
   import subprocess
   fn = "example_requirements.in"
   ret = subprocess.run(["pip-stale", fn], capture_output=True)
   cog.out("\nExample::\n\n")
   cog.outl(f"   $ cat {fn}")
   with open(fn) as fp:
       for line in fp:
           cog.out(f"   {line}")

   cog.outl("")
   cog.outl(f"   $ pip-stale {fn}")
   for line in ret.stdout.decode("utf-8").splitlines():
       if line.strip():
           cog.outl(f"   {line}")
       else:
           cog.outl("")
   cog.outl("")
   ]]]

Example::

   $ cat example_requirements.in
   click==8.0.0
   packaging==23.0
   requests==2.31.0
   rich==13.5.0

   $ pip-stale example_requirements.in
    name      | current version | latest | latest minor | latest patch 
   -----------|-----------------|--------|--------------|--------------
    click     | 8.0.0           | 8.1.7  | 8.1.7        | 8.0.4        
    packaging | 23.0            | 23.2   | 23.2         | 23.0         
    rich      | 13.5.0          | 13.6.0 | 13.6.0       | 13.5.3       

.. [[[end]]]


pip-stale development
=====================

::

    pip install -e '.[dev]'


Then you can do these things::

    make lint
    make test
    make docs


Why not other tools?
====================

Most other libraries I looked at had one or more of the following issues:

* ``pip list --outdated`` is great, but only works with dependencies in the
  environment and doesn't work well when you need to stay on a specific
  major/minor version that isn't the latest; for example Django LTS.
* ``pip-outdated.py``
  (`link <https://www.peterbe.com/plog/pip-outdated.py-with-interactive-upgrade>`__)
  is great, but also doesn't work well when you need to stick to a major
  version that isn't the latest
* ``piprot`` (`link <https://pypi.org/project/piprot/>`__) is abandoned and
  doesn't work anymore
