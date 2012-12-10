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
            'PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui',
            'absolute',
            'absolute.module', 'absolute.module.function',
            'absolute.package', 'absolute.package.module',
            '.', '.relative',
            '..', '..parent_relative',
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
            'PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui',
            'absolute',
            'absolute.module', 'absolute.module.function',
            'absolute.package', 'absolute.package.module',
            'relative.package', 'relative.package.relative',
            'relative', 'relative.parent_relative',
        ])

    def test_parse_init(self):

        names = parse_toplevel_imports(dedent('''
            from .core import is_outdated, reload, autoreload
        '''), 'autoreload', 'autoreload')

        self.assertEqual(names, [
            'autoreload.core',
            'autoreload.core.is_outdated',
            'autoreload.core.reload',
            'autoreload.core.autoreload',
        ])


    def test_path_is_in_directories(self):
        self.assertTrue(path_is_in_directories('/path/to/file', ['/']))
        self.assertTrue(path_is_in_directories('/path/to/file', ['/path']))
        self.assertTrue(path_is_in_directories('/path/to/file', ['/path/to']))
        self.assertTrue(path_is_in_directories('/path/to/file', ['/path/to/file']))
        self.assertFalse(path_is_in_directories('/path/to/file', ['/path/to/file/nope']))
        self.assertFalse(path_is_in_directories('/path/to/file', ['/another/path']))



