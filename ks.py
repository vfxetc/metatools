import os
import sys
import types

for type_, app_name in [
    ('3d', 'maya'),
    ('3d', 'boujou'),
]:
    module = types.ModuleType('.'.join([__name__, app_name]))
    module.__package__ = module.__name__
    module.__path__ = [os.path.abspath(os.path.join(
        __file__,
        os.path.pardir,
        os.path.pardir,
        type_,
        app_name,
        'python',
    ))]
    sys.modules[module.__name__] = module
    globals()[app_name] = module
    
del type_, app_name, module
