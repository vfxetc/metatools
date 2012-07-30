import os
import sys
import types
import re
import imp


_package_paths = dict(

    core='python',
    
    maya='3d/maya/python',
    boujou='3d/boujou/python',
    nuke='2d/nuke/python',
    shake='2d/shake/python',
    
    systems='systems/python',
    
)

_key_base = os.path.abspath(os.path.join(__file__, os.path.pardir, os.path.pardir))


class MetaHook(object):
    
    standalone_re = re.compile(r'^(%s)_(\w+)$' % '|'.join(_package_paths.iterkeys()))
    package_re = re.compile(r'^ks\.(%s)\.(\w+)$' % '|'.join(_package_paths.iterkeys()))
    
    def find_module(self, name, path=None):
        
        print 'metahook', self, name, path
        
        m = self.package_re.match(name) or self.standalone_re.match(name)
        if not m:
            return
        
        package_name, module_name = m.groups()
        if package_name not in _package_paths:
            return
        
        base_path = os.path.join(_key_base, _package_paths[package_name], '%s_%s' % (package_name, module_name))
        
        is_package = False
        path = None
        
        for suffix, mode, module_type in imp.get_suffixes():
            path = os.path.join(base_path, '__init__') + suffix
            if os.path.exists(path):
                is_package = True
                break
            path = base_path + suffix
            if os.path.exists(path):
                break
        else:
            # We didn't find anything.
            return

        return MetaLoader(package_name, module_name, path, module_type, is_package)


class MetaLoader(object):
    
    def __init__(self, package_name, module_name, path, module_type, is_package):
        self.package_name = package_name
        self.module_name = module_name
        self.path = path
        self.module_type = module_type
        self.is_package = is_package
    
    def load_module(self, name):
        
        if self.module_type == imp.PY_SOURCE:
            loader = imp.load_source
        elif self.module_type == imp.PY_COMPILED:
            loader = imp.load_compiled
        elif self.module_type == imp.C_EXTENSION:
            loader = imp.load_dynamic
        else:
            # We can only load those three types.
            return None
        
        print 'loading from', self.path   
        name = '%s_%s' % (self.package_name, self.module_name)
        module = loader(name, self.path)
        
        return module




sys.meta_path.append(MetaHook())


# Create pseudo-package modules.
for package, path in _package_paths.iteritems():
    module = types.ModuleType('.'.join([__name__, package]))
    module.__package__ = module.__name__
    module.__path__ = [os.path.join(_key_base, path)]
    sys.modules[module.__name__] = module
    globals()[package] = module
    
del package, path, module



def test():
    
    print '\n\n\n'
    print 'IMPORT TESTS'
    
    for name in '''
        
        ks.maya.render
        render
        
        ks.nuke.render
        nuke_render
        
        ks.core.environment
        environment
        
    '''.strip().split():
        print
        print name
        print '--------'
        try:
            module = __import__(name, fromlist=['.'])
        except ImportError:
            print 'FAIL'
        else:
            print 'ok:', repr(module.__name__), '->', repr(module.__file__)
    
    print

