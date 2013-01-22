
import functools
import sys
import warnings

from .imports import resolve_relative_name


class AttributeRenamedWarning(UserWarning):
    pass


class FunctionRenamedWarning(UserWarning):
    pass


class ModuleRenamedWarning(UserWarning):
    pass


class renamed_attr(object):

    """Proxy for renamed attributes (or methods) on classes.

    Getting and setting values will be redirected to the provided name,
    and warnings will be issues every time.

    E.g.::

        >>> class Example(object):
        ... 
        ...     new_value = 'something'
        ...     old_value = renamed_attr('new_value')
        ...     
        ...     def new_func(self, a, b):
        ...         return a + b
        ...         
        ...     old_func = renamed_attr('new_func')
        ... 
        >>> e = Example()
        >>>
        >>> e.old_value = 'else'
        # AttributeRenamedWarning: Example.old_value renamed to new_value
        >>>
        >>> e.old_func(1, 2)
        # AttributeRenamedWarning: Example.old_func renamed to new_func
        3

    """

    def __init__(self, new_name):
        self.new_name = new_name
        self._old_name = None # We haven't discovered it yet.

    def old_name(self, cls):
        if self._old_name is None:
            for k, v in vars(cls).iteritems():
                if v is self:
                    self._old_name = k
                    break
        return self._old_name

    def __get__(self, instance, cls):
        old_name = self.old_name(cls)
        warnings.warn('%s.%s was renamed to %s' % (
            cls.__name__, old_name, self.new_name,
        ), AttributeRenamedWarning, stacklevel=2)
        return getattr(instance if instance is not None else cls, self.new_name)

    def __set__(self, instance, value):
        old_name = self.old_name(instance.__class__)
        warnings.warn('%s.%s was renamed to %s' % (
            instance.__class__.__name__, old_name, self.new_name,
        ), AttributeRenamedWarning, stacklevel=2)
        setattr(instance, self.new_name, value)


def renamed_func(func, name=None, module=None):

    if name:
        if module:
            full_name = '%s.%s' % (module, name)
        else:
            full_name = name
    else:
        full_name = None

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if full_name is not None:
            warnings.warn('%s was renamed to %s.%s' % (
                full_name, func.__module__, func.__name__,
            ), FunctionRenamedWarning, stacklevel=2)
        else:
            warnings.warn('renamed to %s.%s' % (
                func.__module__, func.__name__,
            ), FunctionRenamedWarning, stacklevel=2)
        return func(*args, **kwargs)

    if name:
        _wrapper.__name__ = name
    if module:
        _wrapper.__module__ = module
    
    return _wrapper


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





