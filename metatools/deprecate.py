
import sys
import warnings


class ModuleRenamedWarning(UserWarning):
    pass


def module_renamed(new_name):
    """Replace the current module with the one found at the given name.

    ::

        # new.py:
        >>> def func():
        ...     print "Hello from %s!" % __name__

        # old.py:
        >>> from metatools.deprecate import module_renamed
        >>>> module_renamed('new')

        # usage.py:
        >>> from old import func
        # ModuleRenamedWarning: old renamed to new
        >>> func()
        Hello from new!

    """

    frame = sys._getframe(1)
    old_name = frame.f_globals['__name__']

    new_module = __import__(new_name, fromlist=['.'])

    # 3 stacks above is where it was actually imported from.
    warnings.warn('%s renamed to %s' % (old_name, new_name), ModuleRenamedWarning, stacklevel=3)

    sys.modules[old_name] = new_module

