import os


def get_source_path(module):

    path = getattr(module, '__file__', None)

    if not path:
        return

    if path.endswith('.pyc'):
        path = path[:-1]

    if os.path.exists(path):
        return path


def resolve_relative_name(package, module, relative):
    """Convert a relative import path into an absolute one.

    :param str package: The ``__package__`` that we are in.
    :param str module: The ``__name__`` of the module we are in.
    :param str relative: The module name to resolve.

    Absolute names are passed through untouched.

    """

    if relative.startswith('.'):
        
        # Add a dummy module onto the end if this is a package. It will be
        # pulled off in the loop below.
        if package == module:
            module += '.dummy'
        
        parts = module.split('.')
        while relative.startswith('.'):
            relative = relative[1:]
            parts.pop(-1)
        relative = '.'.join(parts) + ('.' if relative else '') + relative

    return relative
