import functools
import warnings


class CallingDeprecatedWarning(UserWarning):
    pass


class Deprecated(object):

    def __init__(self, obj):
        self.obj = obj
        self.name = '%s.%s' % (obj.__module__, obj.__name__)

    def __call__(self, *args, **kwargs):
        warnings.warn('Calling %s has been deprecated' % self.name, CallingDeprecatedWarning, stacklevel=2)
        return self.obj(*args, **kwargs)


def deprecate(obj):
    """Wrap a function so that it will issue a deprecation warning.

    ::

        >>> @metatools.deprecate.deprecate
        ... def old_func():
        ...     print "Hello!"
        ... 
        >>> old_func()
        # CallingDeprecatedWarning: old_func has been deprecated
        Hello!

    """

    wrapper = Deprecated(obj)
    functools.update_wrapper(wrapper, obj)
    return wrapper
