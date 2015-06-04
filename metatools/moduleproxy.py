
class ModuleProxy(object):

    def __init__(self, prefixes, modules):
        self.prefixes = prefixes
        self.modules = modules

    def __getattr__(self, name):
        for prefix in self.prefixes:
            fullname = prefix + name
            for module in self.modules:
                obj = getattr(module, fullname, None)
                if obj is not None:
                    setattr(self, name, obj)
                    return obj
        raise AttributeError(name)
