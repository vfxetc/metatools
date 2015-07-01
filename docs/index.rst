.. _index:

Meta Tools
==========

.. image:: https://secure.travis-ci.org/westernx/metatools.png
    :alt: Test Status
    :target: http://travis-ci.org/westernx/metatools


"Python about Python"
---------------------

This package contains tools for working with Python source code, or
bootstrapping other tools into the Western X execution environment.
Applications include:

- creating double-clickable OS X applications which launch Python functions
  while respecting development environments;
- creating shell executables which launch Python functions
  while respecting development environments;
- reloading modified code at run-time;
- renaming modules;
- various code quality and/or convention checks or introspections.


Contents
--------

.. toctree::
    :maxdepth: 2

    apps
    entrypoints
    config

    lint

    monkeypatch
    moduleproxy

    imports
    deprecate
