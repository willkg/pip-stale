=========
pip-stale
=========

pip-stale is a tool for looking at a requirements.in file and noting all the
items that are stale.

:Code:          https://github.com/willkg/pip-stale
:Issues:        https://github.com/willkg/pip-stale/issues
:License:       MPL v2


Goals
=====

Goals of pip-stale:

1. works with a ``requirements.in`` file
2. tells you which dependencies are stale and the most recent versions for all
   later major versions are available--works with dependencies when you're
   using LTS or are locked into an older major version
3. straight-forward to use

pip-stale is inspired by `piprot <https://pypi.org/project/piprot/>`__.


Install and run
===============

Install::

    $ pipx install pip-stale

Run::

    $ pip-stale <requirements.in>

Help text::

    [[[cog
    import cog
    ret = subprocess.run(["pip-stale", "--help"])
    cog.outl(ret.stdout.decode("utf-8").strip())
    ]]]
    [[[end]]]


Quick start
===========

Example::

    [[[cog
    import cog
    ret = subprocess.run(["pip-stale", "example_requirements.in"])
    cog.outl("$ pip-stale example_requirements.in")
    cog.outl(ret.stdout.decode("utf-8").strip())
    ]]]
    [[[end]]]


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

* ``pip list --outdated`` is great, but only works with a venv and doesn't work
  well if you're using Django LTS and don't want the latest version.
* ``pip-outdated.py``
  (`link <https://www.peterbe.com/plog/pip-outdated.py-with-interactive-upgrade>`__)
  is great, but also doesn't work well when you need to stay on a major version
  that isn't the latest
* ``piprot`` (`link <https://pypi.org/project/piprot/>`__) is abandoned and
  doesn't work when you need to stick to a major version that isn't the latest
