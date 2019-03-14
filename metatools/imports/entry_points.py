import ast
import re

from .reload import autoreload


class EntryPointMalformed(ValueError):
    pass

class EntryPointImportError(ImportError):
    pass

class EntryPointAttributeError(AttributeError):
    pass

class EntryPointMalformedArgs(ValueError):
    pass

def load_entry_point(entry_point, reload=False, with_args=False):
    """Load a function as defined by an "entry point" string.

    Entry point strings look like:

    - ``package.module:func``
    - ``module:object.method``
    - ``module:func(arguments)``

    :param str entry_point: The string to parse.
    :param bool reload: If the module should be reloaded by :func:`autoreload`;
        ``None`` implies automatic.
    :param bool with_args: If arguments are allowed in the string; this
        changes the return signature.

    :returns: ``func`` or ``(func, args, kwargs)`` if ``with_args``.
    :raises: ``EntryPointImportError`` if the module doesn't exist,
        ``EntryPointAttributeError`` if the attributes don't exit.

    """

    m = re.match(r'''
        (\w+(?:\.\w+)*) # Module.
        :
        (\w+(?:\.\w+)*) # Attributes.
        (?:\((
            .+?         # Arguments.
        )\))?$
    ''', entry_point, flags=re.VERBOSE)

    if not m:
        raise EntryPointMalformed("Malformed entry point.", entry_point)

    module_name, attr_list, args_source = m.groups()

    if args_source and not with_args:
        raise ValueError("Entry point has arguments, but they are not allowed in this context.", entry_point)

    try:
        module = __import__(module_name, fromlist=['.'])
    except ImportError as e:
        raise EntryPointImportError(*e.args)

    # Reload if requested. `reload is None` is automatic. `reload is True`
    # will always reload the direct module.
    if reload or reload is None:
        autoreload(module, force_self=bool(reload))
    
    # Grab the attribute.
    obj = module
    for attr in attr_list.split('.'):
        try:
            obj = getattr(obj, attr)
        except AttributeError as e:
            raise EntryPointAttributeError(*e.args)

    if not with_args:
        return obj

    # Loads args/kwargs.
    if args_source:

        module = ast.parse('__capture__({})'.format(args_source))
        if not isinstance(module, ast.Module):
            raise EntryPointMalformedArgs("Malformed entry point arguments; not a module.", entry_point)
        if len(module.body) != 1:
            raise EntryPointMalformedArgs("Malformed entry point arguments; too many statements.", entry_point)

        call_ = module.body[0].value
        if not isinstance(call_, ast.Call):
            raise EntryPointMalformedArgs("Malformed entry point arguments; not a call.", entry_point)

        try:
            args = [ast.literal_eval(arg) for arg in call_.args]
        except ValueError as e:
            raise EntryPointMalformedArgs("Malformed entry point arguments; malformed arg.", entry_point)

        try:
            kwargs = {kwarg.arg: ast.literal_eval(kwarg.value) for kwarg in call_.keywords}
        except ValueError as e:
            raise EntryPointMalformedArgs("Malformed entry point arguments; malformed kwarg.", entry_point)

    else:
        args = ()
        kwargs = {}

    return obj, args, kwargs


if __name__ == '__main__':

    import sys

    for spec in sys.argv[1:]:
        func, kwargs, args = load_entry_point(spec, with_args=True)
        print func, kwargs, args


