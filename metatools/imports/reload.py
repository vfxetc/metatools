"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.

There are two ways that we use to track if something should be reloaded, the
last modification time of a file, and the last time we reloaded a module.

The modification time is to determine if a module has actually changed, and if
it is newer than a previously seen time, then that module will be reloaded.

Every module reload will store the time at which it reloads (determined at the
start of an autoreload cycle). Then, in another autoreload cycle, another
module can see when it's dependencies changes by comparing its reload time with
the dependency's. If a dependency was reloaded, then reload ourselves as well.

This is not perfect, and it is known to cause numerous issues (e.g. circular
imports cause some strange problems), however we have found that the problems
it brings up are minor in comparison to the speed boost it tends to give us
while in active development.

A better algorithm would construct a full module graph (doing something about
cycles), and iteratively expand the region that must be reloaded. It may cull
those who have not changes, linearize the remaining dependencies and reload
everything in a big chain.

The tricky part is since `module discovery <discovery>`_ does not reveal the
actual intensions of the code, e.g.:

.. digraph:: actual_graph

    {rank=same; "core" "gui" "utils"}

    "__init__" -> "core"

    "core" -> "utils"

    "gui" -> "core"
    "gui" -> "utils"

but all the dependancies that it is actually capable of, e.g.:

.. digraph:: discovered_graph

    {rank=same; "core" "gui" "utils"}

    "__init__" -> "core"

    "core" -> "__init__" [constraint=false]
    "core" -> "utils"

    "gui" -> "__init__" [constraint=false]
    "gui" -> "core"
    "gui" -> "utils"




"""

import __builtin__
import os
import sys
import time

from . import utils
from . import discovery


_VERBOSE = int(os.environ.get('METATOOLS_RELOAD_VERBOSITY', '0'))
_DEVELOP = bool(os.environ.get('METATOOLS_RELOAD_DEVELOP', ''))

# Memoization stores.
_reload_times = {}
_modification_times = {}
_dependency_lists = {}


def __before_reload__():
    return _reload_times, _modification_times, _dependency_lists

def __after_reload__(state):
    for src, dst in zip((_reload_times, _modification_times, _dependency_lists), state):
        dst.update(src)


def _iter_dependencies(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    dependencies = _dependency_lists.get(module.__name__)
    if dependencies is None:

        potential_dependencies = []

        module_path = utils.get_source_path(module)
        package_dir = module_path and utils.get_path_containing_package(module_path)

        # Get the names of top-level imports.
        discovered_names = discovery.get_top_level_imports(module)

        if _VERBOSE > 1:
            print '# TOP-LEVEL IMPORTS for', module.__name__
            for name in discovered_names:
                print '#     ', name

        # Since toplevel imports may be either absolute or relative (unless
        # you are using Python 3 or `from __future__ import absolute_imports`),
        # we need to actually check if it is possible that these imports are
        # related to us.
        if discovered_names:

            module_import_path = [package_dir]

            # Include anywhere on the sys.path that is not the stdlib
            stdlib = os.path.dirname(os.path.__file__)
            for path in sys.path:
                if path == stdlib or (discovery.path_is_in_directories(path, [sys.prefix]) and 'site-packages' not in path):
                    continue
                module_import_path.append(path)

            # Determine which of the discovered dependencies are on this path.
            for discovered_name in discovered_names:

                discovered_module = sys.modules.get(discovered_name)
                if not discovered_module:
                    continue

                discovered_path = utils.get_source_path(discovered_module)
                if not discovered_path:
                    continue

                if discovery.path_is_in_directories(discovered_path, module_import_path):
                    potential_dependencies.append(discovered_name)

        # Pull in manually specified dependencies.
        potential_dependencies.extend(getattr(module, '__also_reload__', []))

        # Finally, get all of the modules.
        dependencies = []
        seen = set()
        for name in potential_dependencies:

            if not name or name in seen:
                continue
            seen.add(name)

            # Try the name as given...
            dependency = sys.modules.get(name)
            if dependency is not None and dependency not in dependencies:
                dependencies.append(dependency)

            # ... and also absolute. We *could* check to see if '__future__.absolute_import'
            # is in the discovered_names, but lets be lazy developers for now.
            absname = utils.resolve_relative_name(module.__package__, module.__name__, name)
            dependency = sys.modules.get(absname)
            if dependency is not None and dependency not in dependencies:
                dependencies.append(dependency)

        _dependency_lists[module.__name__] = dependencies

        if _VERBOSE > 1:
            print '# DEPENDENCIES FOR', module.__name__
            for x in dependencies:
                print '#    ', x.__name__

    for dependency in dependencies:
        yield dependency



def _iter_chain(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    for dependency in _iter_dependencies(module, visited):
        for x in _iter_chain(dependency, visited):
            yield x
    yield module




def _is_outdated(module):

    file_path = utils.get_source_path(module)

    if file_path is not None:
        
        # Determine if we should reload via mtimes.
        last_modified_time = _modification_times.get(file_path)
        modified_time = os.path.getmtime(file_path)

        _modification_times[file_path] = modified_time
        
        if last_modified_time and last_modified_time < modified_time:
            return True
    
    return False


def is_outdated(module, recursive=True):
    '''Has the source of given module or any of its dependencies changed on disk?'''
    mods = _iter_chain(module) if recursive else [module]
    return any(_is_outdated(mod) for mod in mods)




def reload(module, _time=None):
    '''reload(module)

    Reload the given module, allowing it to retain state across the reload.

    This is effectively a drop-in replacement for the built-in ``reload``
    function, except it plays well with :func:`autoreload`.

    If there is a ``__before_reload__`` function in the module, it will be
    called before reload.

    If there is a ``__after_reload__`` function, it will be called after
    the reload, and it will receive the return value from ``__before_reload__``.

    '''

    print '# autoreload: Reloading: %s at 0x%x' % (module.__name__, id(module))
        
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
        
    __builtin__.reload(module)
    
    # Wipe the dependency cache.
    _dependency_lists.pop(module.__name__, None)

    # Remember when it was reloaded.
    _reload_times[module.__name__] = _time or time.time()()
    if _VERBOSE > 1:
        print '\n'.join('%s: %s' % (t, n) for n, t in sorted(_reload_times.iteritems()))

    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module, force_self=None, _visited=None, _depth=0, _time=None):
    '''autoreload(module, force_self=None)

    Reload the given module if it, or any of its dependencies have new source code.

    :param module: The module to reload if there are changes.
    :param force_self: Reload this module even if there are no dependency changes.
    :return: ``True`` if the module was reloaded.
    
    '''

    if _visited is None:
        _visited = set()

        # Lets hijack this signal to test ourselves.
        if _DEVELOP:
            m = sys.modules[__name__]
            if autoreload(m, None, _visited):
                print '# autoreload: Restarting after self-reload.'
                return m.autoreload(module, force_self, _visited)
    
    # Make sure to not hit the same module twice. Don't need to add it to
    # visited because _iter_dependencies will do that.
    if module.__name__ in _visited:
        return
    _visited.add(module.__name__)

    _time = _time or time.time()

    if _VERBOSE:
        if not _depth:
            print '# autoreload:', module.__name__
        print '# autoreload: -->' + '  ' * _depth, module.__name__

    my_time = _reload_times.get(module.__name__)
    if _VERBOSE and my_time:
        print '# autoreload: %s last reloaded at %s' % (module.__name__, my_time)

    # Give all dependencies a chance to reload.
    dependency_reloaded = False
    for dependency in _iter_dependencies(module):
        dependency_reloaded = autoreload(dependency, _visited=_visited, _depth=_depth+1, _time=_time) or dependency_reloaded

        # Reload if the dependency has been reloaded before us, even if not this time.
        if not dependency_reloaded:
            dependency_time = _reload_times.get(dependency.__name__)
            dependency_reloaded = dependency_time and (not my_time or dependency_time > my_time)
            if dependency_reloaded and _VERBOSE > 1:
                print '# autoreload: dependency %s of %s was previously reloaded' % (dependency.__name__, module.__name__)
    
    # Reload ourselves if any dependencies did, or if we are out of date.
    if force_self or dependency_reloaded or _is_outdated(module):
        reload(module, _time=_time)
        return True

