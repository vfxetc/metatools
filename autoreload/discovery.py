import os
import ast

from . import utils


def get_toplevel_imports(module):
    """Get the imports at the top-level of the given Python module.

    :param module: An actual module; not the name.
    :returns list: The absolute names of everything imported,

    """

    path = getattr(module, '__file__')

    # Go for the original source, not the precomiled one.
    if path and path.endswith('.pyc'):
        path = path[:-4] + '.py'

    # Make sure we have something.
    if not path or not os.path.exists(path):
        return []

    return parse_toplevel_imports(
        path,
        getattr(module, '__package__'),
        getattr(module, '__name__'),
    )


def parse_toplevel_imports(source, package=None, module=None):
    """Get the imports at the top-level of the given Python module.

    :param str source: Python source code.
    :param str package: The ``__package__`` this source is from.
    :param str module: The ``__name__`` this source is from.

    :returns list: The names of everything imported; absolute if package
        and module are provided.

    """

    names = []

    mod_ast = ast.parse(source)
    for node in mod_ast.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module + '.' if node.module else ''
            base += '.' * node.level
            names.extend(base + alias.name for alias in node.names)

    if package is not None and module is not None:
        names = [utils.resolve_relative_name(package, module, name) for name in names]

    return names


