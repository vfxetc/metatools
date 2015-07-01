from .reload import autoreload


def load_entry_point(entry_point, reload=False):
    
    # Parse the entry_point.
    parts = entry_point.split(':')
    if len(parts) != 2:
        raise ValueError('Entry point must look like "package.module:function"; got %r' % entry_point)
    
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

