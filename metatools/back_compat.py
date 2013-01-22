
import functools
import sys
import warnings

from .imports import resolve_relative_name


class ModuleRenamedWarning(UserWarning):
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
    old_package = frame.f_globals.get('__package__')
    new_name = resolve_relative_name(old_package, old_name, new_name)

    # 3 stacks above is where it was actually imported from. Warn before import
    # so that it will still go through even if the import is bad.
    warnings.warn('%s was renamed to %s' % (old_name, new_name), ModuleRenamedWarning, stacklevel=3)

    new_module = __import__(new_name, fromlist=['.'])

    # The actual redirect is here. In CPython this will result in the initial
    # import statement returning the new module instead of the old one.
    sys.modules[old_name] = new_module





