"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.
    
"""

import __builtin__
import itertools
import os
import sys

from .utils import resolve_relative_name


def _iter_children(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    for name in getattr(module, '__also_reload__', []):
        name = resolve_relative_name(module.__package__, module.__name__, name)
        child = sys.modules.get(name)
        if child is not None:
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


_reload_times = {}


def _is_outdated(module):
    
    # Find the file that this comes from.
    file_path = getattr(module, '__file__', '<notafile>')
    if file_path.endswith('.pyc') and os.path.exists(file_path[:-1]):
        file_path = file_path[:-1]
    elif not os.path.exists(file_path):
        file_path = None
    
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
    
    print '# Reloading: %s at 0x%x' % (module.__name__, id(module))
        
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
        
    __builtin__.reload(module)
        
    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module, visited=None, force_self=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice. Don't need to add it to
    # visited because _iter_children will do that.
    if module.__name__ in visited:
        return
    
    # Give all children a chance to reload.
    child_reloaded = False
    for child in _iter_children(module, visited):
        child_reloaded = autoreload(child, visited) or child_reloaded
    
    # Reload ourselves if any children did, or if we are out of date.
    if force_self or child_reloaded or _is_outdated(module):
        reload(module)
        return True


