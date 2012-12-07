import os
import ast

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


def parse_toplevel_imports(source):
    """Get the imports at the top-level of the given Python module.

    :param str source: Python source code.
    :returns list: The relative names of everything imported.

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

    return names


