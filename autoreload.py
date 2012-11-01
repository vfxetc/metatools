"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.
    
"""

import __builtin__
import itertools
import os
import sys




def _resolve_relative_name(module, relative):
    if relative.startswith('.'):
        parts = module.split('.')
        while relative.startswith('.'):
            relative = relative[1:]
            parts.pop(-1)
        relative = '.'.join(parts) + '.' + relative
    return relative


def _iter_chain(module, visited=None):
    
    if visited is None:
        visited = set()
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    for name in getattr(module, '__also_reload__', []):
        name = _resolve_relative_name(module.__name__, name)
        child = sys.modules.get(name)
        if child is not None:
            for x in _iter_chain(child, visited):
                yield x
    yield module


def _is_outdated(module, reload_times):
    
    # Find the file that this comes from.
    file_path = getattr(module, '__file__', '<notafile>')
    if file_path.endswith('.pyc') and os.path.exists(file_path[:-1]):
        file_path = file_path[:-1]
    elif not os.path.exists(file_path):
        file_path = None
    
    if file_path is not None:
        
        # Determine if we should reload via mtimes.
        last_reload_time   = reload_times.get(file_path)
        last_modified_time = os.path.getmtime(file_path)
        
        reload_times[file_path] = last_modified_time
        
        if last_reload_time and last_reload_time < last_modified_time:
            return True
    
    return False


_reload_times = {}


def is_outdated(module, recursive=True):
    mods = _iter_chain(module) if recursive else [module]
    reload_times = _reload_times.setdefault(module.__name__, {})
    return any(_is_outdated(mod, reload_times) for mod in mods)


def reload(module):
    
    for mod in _iter_chain(module):
        print '# Reloading: %s at 0x%x' % (mod.__name__, id(mod))
        
        state = None
        if hasattr(mod, '__before_reload__'):
            state = mod.__before_reload__()
        
        __builtin__.reload(mod)
        
        if hasattr(mod, '__after_reload__'):
            mod.__after_reload__(state)


def autoreload(module):
    if is_outdated(module):
        reload(module)

