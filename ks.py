import imp
import os
import re
import sys
import types


# For direct testing, this controls if print statements execute.
__verbose__ = False


# The absolute root of the key_base.
key_base_root = os.path.abspath(os.path.join(__file__, os.path.pardir, os.path.pardir))


# Dict mapping namespaces to absolute paths to import from...
namespace_paths = dict((k, os.path.join(key_base_root, v)) for k, v in dict(
    
    #... built from paths relative to the key_base root.
    boujou='3d/boujou/python',
    core='python',
    maya='3d/maya/python',
    nuke='2d/nuke/python',
    shake='2d/shake/python',
    systems='systems/python',
        
).iteritems())


class NamespaceHook(object):
    
    def find_module(self, namespaced_name, path=None):
        
        parts = namespaced_name.split('.')
        
        # We only deal with our namespaces and immediate modules.
        if len(parts) > 3:
            return
        
        # We only deal with the "ks" package.
        if parts[0] != 'ks':
            return
        
        # We only deal with our own namespaces.
        if parts[1] not in namespace_paths:
            return
        
        # The namespaced are handled by NamespaceLoader quite simply.
        if len(parts) == 2:
            return NamespaceLoader()
        
        if __verbose__:
            print self.__class__.__name__, 'looking for', repr(namespaced_name), 'on', path
            
        _, namespace, module_name = parts
        namespace_path = namespace_paths[namespace]
        
        # If we import "ks.nuke.render", actually look for "ks_nuke_render",
        # "nuke_render", and finally "render" in the "2d/nuke/python" directory.
        for real_name in ['ks_%s_%s' % (namespace, module_name), '%s_%s' % (namespace, module_name), module_name]:
            
            try:
                file, path, description = imp.find_module(real_name, [namespace_path])
            except ImportError:
                continue
            
            return ModuleLoader(namespaced_name, real_name, file, path, description)
        
        

class NamespaceLoader(object):
        
    def load_module(self, name):
        
        if __verbose__:
            print 'INITIALIZING NAMESPACE', name
        
        # Setup a dummy module.
        module = types.ModuleType(name)
        module.__package__ = module.__name__
        module.__path__ = [] # It is a package, but we will deal with the path.
        
        # Set it.
        sys.modules[name] = module
        
        return module


class ModuleLoader(object):
    
    def __init__(self, namespaced_name, real_name, file, path, description):
        self.namespaced_name = namespaced_name
        self.real_name = real_name
        self.file = file
        self.path = path
        self.description = description
    
    def load_module(self, name):
        
        if __verbose__:
            print self.__class__.__name__, 'loading', repr(self.real_name), 'from', repr(self.path), 'via', repr(self.description)
        
        # See if it already exists in non-namespaced form.
        if self.real_name in sys.modules:
            
            # Canonicalize the path of the existing module.
            path = sys.modules[self.real_name].__file__
            path = os.path.splitext(path)[0]
            if path.endswith('__init__'):
                path = os.path.dirname(path)
            
            # It matches?!
            if path == os.path.splitext(self.path)[0]:
                module = sys.modules[self.real_name]
                sys.modules.setdefault(self.namespaced_name, module)
                return module
        
        # Create our stub of a module. If it is in sys.modules then the import
        # machinery will effectively reload upon it.
        module = imp.new_module(self.real_name)
        sys.modules.setdefault(self.namespaced_name, module)
        sys.modules.setdefault(self.real_name, module)
        
        # Make sure this knows it is part of a larger entity.
        
        # Manually set the package path, since the load_module won't handle this
        # for us since we put a stub into sys.modules.
        if self.description[-1] == imp.PKG_DIRECTORY:
            module.__path__ = [self.path]
            module.__package__ = self.namespaced_name
        else:
            module.__package__ = self.namespaced_name.split('.', 1)[0]
            
        # Finally load it.
        return imp.load_module(self.namespaced_name, self.file, self.path, self.description)
        


# Add the path attribute so that the import mechanism treats this as a package.
__path__ = []


# Register our hook.
sys.meta_path.append(NamespaceHook())


def test():
    
    global __verbose__
    __verbose__ = True
    
    import traceback
    
    
    print '\n\n\n'
    print 'IMPORT TESTS'
    
    for namespaced, canonical in [
        ('ks.core.environment', 'environment'),
        ('ks.maya.render', 'render'),
        ('ks.nuke.render', 'nuke_render'),
        ('key_tools_global', 'ks.core.key_tools_global'),
    ]:
        
        print
        print namespaced
        print '--------'
        try:
            module1 = __import__(namespaced, fromlist=['.'])
            module2 = __import__(canonical, fromlist=['.'])
            module3 = __import__(namespaced, fromlist=['.'])
            module4 = __import__(canonical, fromlist=['.'])
        except ImportError, e:
            print 'FAIL', repr(e)
            traceback.print_exc()
        else:
            if module1 is not module2:
                print 'FAIL', 'modules are independant'
                print '\t', module1.__name__, repr(module1.__file__)
                print '\t', module2.__name__, repr(module1.__file__)
            else:
                print 'ok:', repr(module1.__name__), '->', repr(module1.__file__)
    
    print
    
    print 'NAMESPACED'
    import ks.core.importtest
    print 'DIRECT'
    import importtest
    print 'RELOAD'
    reload(ks.core.importtest)

