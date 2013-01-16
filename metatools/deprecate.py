
import functools
import sys
import warnings


class ModuleRenamedWarning(UserWarning):
    pass

class FunctionDeprecatedWarning(UserWarning):
    pass


def module_renamed(new_name):
    """Replace the current module with the one found at the given name.

    Issues a :class:`ModuleRenamedWarning`.

    For example,

    ``new.py``::

        >>> def func():
        ...     print "Hello from %s!" % __name__

    ``old.py``::

        >>> from metatools.deprecate import module_renamed
        >>>> module_renamed('new')

    ``use.py``::

        >>> from old import func
        # ModuleRenamedWarning: old was renamed to new
        >>> func()
        Hello from new!

    """

    frame = sys._getframe(1)
    old_name = frame.f_globals['__name__']

    new_module = __import__(new_name, fromlist=['.'])

    # 3 stacks above is where it was actually imported from.
    warnings.warn('%s was renamed to %s' % (old_name, new_name), ModuleRenamedWarning, stacklevel=3)

    sys.modules[old_name] = new_module


def decorate(func):
    """Wrap a function so that it will issue a deprecation warning.

    ::

        >>> @metatools.deprecate.decorate
        ... def old_func():
        ...     print "Hello!"
        ... 
        >>> old_func()
        # FunctionDeprecatedWarning: old_func has been deprecated
        Hello!

    """

    @functools.wraps(func)
    def _deprecated(*args, **kwargs):
        warnings.warn('%s has been deprecated' % func.__name__, FunctionDeprecatedWarning, stacklevel=2)
        return func(*args, **kwargs)

    return _deprecated


