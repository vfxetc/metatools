# autoreload

Python tools for automatic module reloading for testing and production.

[![Test Status](https://secure.travis-ci.org/westernx/autoreload.png)](http://travis-ci.org/westernx/autoreload)

This package provides an `autoreload` method which scans the import heirarchy of the given module, and reloads those dependencies which have been updated on disk.

It only checks for modules within the same entry on `sys.path`, or within the same segment of `$KS_PYTHON_SITES` (if present), or within the entirety of `$KS_TOOLS` (if present).

Additional modules can be specified via a list of names in a `__also_reload__` top-level attribute.

A `__before_reload__` function on a module will be called before it is reloaded, and the results (or `None`) will be passed to a `__after_reload__` function on the module ater it is reloaded.
