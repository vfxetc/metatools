from .reload import is_outdated, reload, autoreload
from .utils import resolve_relative_name

# Silence pyflakes
assert is_outdated and reload and autoreload and resolve_relative_name


def load_entrypoint(entrypoint, reload=False):
    
    # Parse the entrypoint.
    parts = entrypoint.split(':')
    if len(parts) != 2:
        raise ValueError('Entrypoint must look like "package.module:function"; got %r' % entrypoint)
    
    module_name, attribute = parts
    
    # If we can't directly import it, then import the package and get the
    # module via attribute access. This is because of the `code` sub-package
    # on many of the older tools.
    try:
        module = __import__(module_name, fromlist=['.'])
    except ImportError as ie:
        parts = module_name.rsplit('.', 1)
        if len(parts) == 1:
            raise ie
        package_name, module_name = parts
        package = __import__(package_name, fromlist=['.'])
        module = getattr(package, module_name, None)
        if module is None:
            raise
        
    # Reload if requested. `reload is None` is automatic. `reload is True`
    # will always reload the direct module.
    if reload or reload is None:
        autoreload(module, force_self=bool(reload))
        
    # Grab the function.
    try:
        return getattr(module, attribute)
    except AttributeError:
        raise ValueError('%r module has no %r attribute' % (module.__name__, attribute))
