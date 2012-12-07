"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.
    
"""

import __builtin__
import itertools
import os
import sys

from . import utils
from . import discovery


# Memoization stores.
_reload_times = {}
_child_lists = {}


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
        
        # print '# DISCOVERY for', module.__name__
        # for name in discovered_names:
        #     print '#     ', name

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

        # print '# DEPENDENCIES FOR', module.__name__
        # for x in dependencies:
        #     print '#    ', x.__name__

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
        last_reload_time   = _reload_times.get(file_path)
        last_modified_time = os.path.getmtime(file_path)
        
        _reload_times[file_path] = last_modified_time
        
        if last_reload_time and last_reload_time < last_modified_time:
            return True
    
    return False


def is_outdated(module, recursive=True):
    mods = _iter_chain(module) if recursive else [module]
    return any(_is_outdated(mod) for mod in mods)


def reload(module):
    
    print '# autoreload: Reloading: %s at 0x%x' % (module.__name__, id(module))
        
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
        
    __builtin__.reload(module)
    
    # Wipe the child cache.
    _child_lists.pop(module.__name__, None)

    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module, visited=None, force_self=None, _depth=0):
    

    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice. Don't need to add it to
    # visited because _iter_children will do that.
    if module.__name__ in visited:
        return
    
    # if not _depth:
    #     print '# autoreload:', module.__name__
    # print '# autoreload: -->' + '  ' * _depth, module.__name__

    # Give all children a chance to reload.
    child_reloaded = False
    for child in _iter_children(module, visited):
        child_reloaded = autoreload(child, visited, _depth=_depth+1) or child_reloaded
    
    # Reload ourselves if any children did, or if we are out of date.
    if force_self or child_reloaded or _is_outdated(module):
        reload(module)
        return True


