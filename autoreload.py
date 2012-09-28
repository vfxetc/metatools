"""Automatically reloading modules when their source has been updated.

This also allows for some state retention in reloaded modules, for modules
to specify dependencies that must be checked for being outdated as well, and to
unload those dependencies on reload.
    
"""

import __builtin__
import os
import sys


_reload_times = {}


def _resolve_relative_name(module, relative):
    if relative.startswith('.'):
        parts = module.split('.')
        while relative.startswith('.'):
            relative = relative[1:]
            parts.pop(-1)
        relative = '.'.join(parts) + '.' + relative
    return relative


def _unload_associated(module, visited):
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
    associates = getattr(module, '__also_reload__', [])
    for name in associates:
        name = _resolve_relative_name(module.__name__, name)
        child_module = sys.modules.get(name)
        if child_module is not None:
            print '# Unloading:', name, 'at 0x%x' % id(child_module)
            if hasattr(child_module, '__before_unload__'):
                child_module.__before_unload__()
            _unload_associated(child_module, visited)
            for k, v in sys.modules.items():
                if child_module is v:
                    if k != name:
                        print '# Unloading:', name, 'A.K.A.', k
                    del sys.modules[k]


def unload_associated(module):
    _unload_associated(module, set())


def is_outdated(module):
    return _is_outdated(module, set())

def _is_outdated(module, visited):
    
    # Make sure to not hit the same module twice.
    if module.__name__ in visited:
        return
    visited.add(module.__name__)
    
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
    
    # Check associates.
    associates = getattr(module, '__also_reload__', [])
    for name in associates:
        name = _resolve_relative_name(module.__name__, name)
        child_module = sys.modules.get(name)
        if child_module is not None and _is_outdated(child_module, visited):
            return True


def reload(module):
    
    state = None
    if hasattr(module, '__before_reload__'):
        state = module.__before_reload__()
    
    # Unload requested modules.
    unload_associated(module)
    
    print '# Reloading:', module.__name__, 'at 0x%x' % id(module)
    __builtin__.reload(module)
    
    if hasattr(module, '__after_reload__'):
        module.__after_reload__(state)


def autoreload(module):
    if is_outdated(module):
        reload(module)

