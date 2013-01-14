"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.

This is not perfect, and it is known to cause numerous issues, however we have
found that the problems it brings up are minor in comparison to the speed boost
it tends to give us.

There are two ways that we use to track if something should be reloaded, the
last modification time of a file, and an abstract counter for when modules
reloaded relative to each other.

The modification time is to determine if a module has actually changed, and if
it is newer than a previously seen time, then that module will be reloaded.

Every module reload will store a "counter" which is higher than all other
counters (determined at the start of an autoreload cycle). Then, in another
autoreload cycle, another module can see when it's dependencies changes by
comparing its counter with the dependencies. If a dependency was reloaded, then
reload ourselves and set our counter a little higher.

"""

import __builtin__
import os
import sys
import itertools

from . import utils
from . import discovery


_VERBOSE = False

# Memoization stores.
_reload_counters = {}
_modification_counters = {}
_child_lists = {}


def __before_reload__():
    return _reload_counters, _modification_counters, _child_lists


def __after_reload__(state):
    state = state or ()
    for src, dst in zip(state, (_reload_counters, _modification_counters, _child_lists)):
        for k, v in src.iteritems():
            dst.setdefault(k, v)


def _next_counter():
    if not _reload_counters:
        return 1
    else:
        return 1 + max(_reload_counters.itervalues())


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
            print '# DISCOVERY for', module.__name__
            for name in discovered_names:
                print '#     ', name

        if discovered_names:

            # Look in $KS_TOOLS, if it is set.
            include_path = [os.environ.get('KS_TOOLS')]

            # Include anywhere on $KS_PYTHON_SITES that we could have
            # been imported from.
            include_path.extend(x for x in os.environ.get('KS_PYTHON_SITES', '').split(':') if
                x and discovery.path_is_in_directories(path, [x])
            )

            # Include anywhere on the path that we could have been
            # imported from.
            include_path.extend(x for x in sys.path if
                discovery.path_is_in_directories(path, [x])
            )

            # Finally, determime which of the discovered children are
            # on this path.
            include_path = filter(None, include_path)
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
            print '# DEPENDENCIES FOR', module.__name__
            for x in dependencies:
                print '#    ', x.__name__

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
        last_modified_counter   = _modification_counters.get(file_path)
        modified_counter = os.path.getmtime(file_path)
        
        _modification_counters[file_path] = modified_counter
        
        if last_modified_counter and last_modified_counter < modified_counter:
            return True
    
    return False


def is_outdated(module, recursive=True):
    mods = _iter_chain(module) if recursive else [module]
    return any(_is_outdated(mod) for mod in mods)




def reload(module, _counter=None):
    
    print '# autoreload: Reloading: %s at 0x%x' % (module.__name__, id(module))
        
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
        
    __builtin__.reload(module)
    
    # Wipe the child cache.
    _child_lists.pop(module.__name__, None)

    # Remember when it was reloaded.
    _reload_counters[module.__name__] = _counter or _next_counter()
    if _VERBOSE:
        print '\n'.join('%s: %s' % (t, n) for n, t in sorted(_reload_counters.iteritems()))

    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module, visited=None, force_self=None, _depth=0, _counter=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice. Don't need to add it to
    # visited because _iter_children will do that.
    if module.__name__ in visited:
        return
    
    _counter = _counter or _next_counter()

    if _VERBOSE:
        if not _depth:
            print '# autoreload:', module.__name__
        print '# autoreload: -->' + '  ' * _depth, module.__name__

    my_counter = _reload_counters.get(module.__name__)
    if _VERBOSE and my_counter:
        print '# autoreload: %s last reloaded at %s' % (module.__name__, my_counter)

    # Give all children a chance to reload.
    child_reloaded = False
    for child in _iter_children(module, visited):
        child_reloaded = autoreload(child, visited, _depth=_depth+1, _counter=_counter) or child_reloaded

        # Reload if the child has been reloaded before us, even if not this time.
        if not child_reloaded:
            child_counter = _reload_counters.get(child.__name__)
            child_reloaded = child_counter and (not my_counter or child_counter > my_counter)
            if child_reloaded:
                print '# autoreload: Child %s of %s was previously reloaded' % (child.__name__, module.__name__)
    
    # Reload ourselves if any children did, or if we are out of date.
    if force_self or child_reloaded or _is_outdated(module):
        reload(module, _counter=_counter)
        return True

