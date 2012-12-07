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


