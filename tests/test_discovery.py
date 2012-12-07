from common import *

from autoreload.discovery import *


class TestDiscovery(TestCase):

    def test_parse_relative(self):

        names = parse_toplevel_imports(dedent('''

            import os
            import sys

            from PyQt4 import QtCore, QtGui

            import absolute
            from absolute.module import function
            from absolute.package import module
            from . import relative
            from .. import parent_relative

        '''))

        self.assertEqual(names, [
            'os', 'sys',
            'PyQt4.QtCore', 'PyQt4.QtGui',
            'absolute',
            'absolute.module.function',
            'absolute.package.module',
            '.relative',
            '..parent_relative',
        ])

    def test_parse_absolute(self):

        names = parse_toplevel_imports(dedent('''

            import os
            import sys

            from PyQt4 import QtCore, QtGui

            import absolute
            from absolute.module import function
            from absolute.package import module
            from . import relative
            from .. import parent_relative

        '''), 'relative.package', 'relative.package.module')

        self.assertEqual(names, [
            'os', 'sys',
            'PyQt4.QtCore', 'PyQt4.QtGui',
            'absolute',
            'absolute.module.function',
            'absolute.package.module',
            'relative.package.relative',
            'relative.parent_relative',
        ])

    def test_path_is_in_directory(self):
        self.assertTrue(path_is_in_directory('/path/to/file', '/'))
        self.assertTrue(path_is_in_directory('/path/to/file', '/path'))
        self.assertTrue(path_is_in_directory('/path/to/file', '/path/to'))
        self.assertTrue(path_is_in_directory('/path/to/file', '/path/to/file'))
        self.assertFalse(path_is_in_directory('/path/to/file', '/path/to/file/nope'))
        self.assertFalse(path_is_in_directory('/path/to/file', '/another/path'))

    def test_module_is_in_directories(self):

        name = __name__
        directory = os.path.dirname(os.path.abspath(__file__))

        self.assertFalse(module_is_in_directories('does.not.exist', ['/']))

        self.assertTrue(module_is_in_directories(name, ['/']))
        self.assertTrue(module_is_in_directories(name, [directory]))
        self.assertFalse(module_is_in_directories(name, [os.path.join(directory, 'subdirectory')]))



