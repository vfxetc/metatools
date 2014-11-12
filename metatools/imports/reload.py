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

A better algorithm would construct a full module graph (it would not be
acyclic), and iteratively expand the region that must be reloaded. Then it
would linearize the dependencies and reload everything in a big chain.

The tricky part is since `module discovery <discovery>` does not reveal the
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

from __future__ import print_function

import os
import sys
import time

if sys.version_info[0] > 2:
    from imp import reload as _reload
else:
    from __builtin__ import reload as _reload

from . import utils
from . import discovery


_VERBOSE = False

# Memoization stores.
_reload_times = {}
_modification_times = {}
_child_lists = {}


def __before_reload__():
    return _reload_times, _modification_times, _child_lists


def __after_reload__(state):
    state = state or ()
    for src, dst in zip(state, (_reload_times, _modification_times, _child_lists)):
        for k, v in src.iteritems():
            dst.setdefault(k, v)


def _iter_children(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    dependencies = _child_lists.get(module.__name__)
    if dependencies is None:

        children = []

        path = utils.get_source_path(module)

        # Get the absolute names of top-level imports.
        discovered_names = discovery.get_toplevel_imports(module)
        
        if _VERBOSE:
            print('# DISCOVERY for', module.__name__)
            for name in discovered_names:
                print('#     ', name)

        if discovered_names:

            # Look in $KS_TOOLS, if it is set.
            include_path = [os.environ.get('KS_TOOLS')]

            # Include anywhere on $KS_PYTHON_SITES that we could have
            # been imported from.
            include_path.extend(x for x in os.environ.get('KS_SITES', '').split(':') if
                x and discovery.path_is_in_directories(path, [x])
            )

            # Include anywhere on the path that we could have been
            # imported from.
            include_path.extend(x for x in sys.path if
                discovery.path_is_in_directories(path, [x])
            )

            # Finally, determine which of the discovered children are
            # on this path.
            include_path = [x for x in include_path if x]
            for discovered_name in discovered_names:
                discovered_module = sys.modules.get(discovered_name)
                discovered_path = discovered_module and utils.get_source_path(discovered_module)
                if discovered_path and discovery.path_is_in_directories(discovered_path, include_path):
                    children.append(discovered_name)

        # Manually specified children.
        children.extend(getattr(module, '__also_reload__', []))

        # Resolve them all.
        children = [
            utils.resolve_relative_name(module.__package__, module.__name__, name)
            for name in children
            if name
        ]

        # Finally, get all of the modules.
        dependencies = []
        seen = set()
        for name in children:

            if name in seen:
                continue
            seen.add(name)

            dependency = sys.modules.get(name)
            if dependency is not None:
                dependencies.append(dependency)

        _child_lists[module.__name__] = dependencies

        if _VERBOSE:
            print('# DEPENDENCIES FOR', module.__name__)
            for x in dependencies:
                print('#    ', x.__name__)

    for child in dependencies:
        yield child



def _iter_chain(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    for child in _iter_children(module, visited):
        for x in _iter_chain(child, visited):
            yield x
    yield module




def _is_outdated(module):
    
    file_path = utils.get_source_path(module)
    if file_path is not None:
        
        # Determine if we should reload via mtimes.
        last_modified_time   = _modification_times.get(file_path)
        modified_time = os.path.getmtime(file_path)
        
        _modification_times[file_path] = modified_time
        
        if last_modified_time and last_modified_time < modified_time:
            return True
    
    return False


def is_outdated(module, recursive=True):
    mods = _iter_chain(module) if recursive else [module]
    return any(_is_outdated(mod) for mod in mods)




def reload(module, _time=None):
    
    print('# autoreload: Reloading: %s at 0x%x' % (module.__name__, id(module)))
        
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
        
    _reload(module)
    
    # Wipe the child cache.
    _child_lists.pop(module.__name__, None)

    # Remember when it was reloaded.
    _reload_times[module.__name__] = _time or time.time()()
    if _VERBOSE:
        print('\n'.join('%s: %s' % (t, n) for n, t in sorted(_reload_times.iteritems())))

    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module, visited=None, force_self=None, _depth=0, _time=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice. Don't need to add it to
    # visited because _iter_children will do that.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    _time = _time or time.time()

    if _VERBOSE:
        if not _depth:
            print('# autoreload:', module.__name__)
        print('# autoreload: -->' + '  ' * _depth, module.__name__)

    my_time = _reload_times.get(module.__name__)
    if _VERBOSE and my_time:
        print('# autoreload: %s last reloaded at %s' % (module.__name__, my_time))

    # Give all children a chance to reload.
    child_reloaded = False
    for child in _iter_children(module):
        child_reloaded = autoreload(child, visited, _depth=_depth+1, _time=_time) or child_reloaded

        # Reload if the child has been reloaded before us, even if not this time.
        if not child_reloaded:
            child_time = _reload_times.get(child.__name__)
            child_reloaded = child_time and (not my_time or child_time > my_time)
            if child_reloaded:
                print('# autoreload: Child %s of %s was previously reloaded' % (child.__name__, module.__name__))
    
    # Reload ourselves if any children did, or if we are out of date.
    if force_self or child_reloaded or _is_outdated(module):
        reload(module, _time=_time)
        return True

