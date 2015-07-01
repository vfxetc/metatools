import os
import ast

from . import utils


def get_toplevel_imports(module):
    """Get the imports at the top-level of the given Python module.

    :param module: An actual module; not the name.
    :returns list: The absolute names of everything imported,

    """


    path = utils.get_source_path(module)

    if path is None:
        return []

    # We can't tell with compiled modules.
    if os.path.splitext(path)[1] != '.py':
        return []

    return parse_imports(
        open(path).read(),
        getattr(module, '__package__'),
        getattr(module, '__name__'),
        path=path,
    )


def parse_imports(source, package=None, module=None, path=None, toplevel=True):
    """Get the imports at the top-level of the given Python module.

    :param str source: Python source code.
    :param str package: The ``__package__`` this source is from.
    :param str module: The ``__name__`` this source is from.
    :param bool toplevel: Walk the full AST, or only look at the top-level?
    :returns list: The names of everything imported; absolute if package
        and module are provided.

    """

    names = []

    try:
        # Discard all trailing whitespace to avoid syntax errors due to
        # too much white in the last line.
        mod_ast = ast.parse(source.rstrip())
    except (TypeError, SyntaxError) as e:
        print '# %s: %s in %s: %s' % (__name__, e.__class__.__name__, path, e)
        return []

    for node in ast.walk(mod_ast) if not toplevel else mod_ast.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = '.' * node.level + (node.module or '')
            names.append(base)
            if node.module:
                base += '.'
            names.extend(base + alias.name for alias in node.names)

    if package is not None and module is not None:
        names = [utils.resolve_relative_name(package, module, name) for name in names]

    return names


def path_is_in_directories(path, directories):
    """Is the given path within the given directories?

    :param str path: The path to test.
    :param list directories: The directories to test if the path is in.
    :returns bool:

    """
    path = os.path.abspath(path) + os.path.sep
    for dir_ in directories:
        dir_ = os.path.abspath(dir_) + os.path.sep
        if path.startswith(dir_):
            return True


