from common import *

from autoreload.utils import *


class TestRelativeNames(TestCase):

    def test_abs_names(self):

        self.assertEqual(
            resolve_relative_name('package', 'module', 'a.b.c'),
            'a.b.c',
        )

        # This is an expected error case.
        self.assertEqual(
            resolve_relative_name('package', 'module', '.b.c'),
            '.b.c',
        )

    def test_relative(self):

        self.assertEqual(
            resolve_relative_name('package', 'package.module', '.'),
            'package',
        )
        self.assertEqual(
            resolve_relative_name('package', 'package', '.'),
            'package',
        )

    def test_from_module(self):

        self.assertEqual(
            resolve_relative_name('package', 'package.module', '.a'),
            'package.a',
        )
        
        self.assertEqual(
            resolve_relative_name('package.sub', 'package.sub.module', '.a'),
            'package.sub.a',
        )

        self.assertEqual(
            resolve_relative_name('package.sub', 'package.sub.module', '..a'),
            'package.a',
        )

    def test_from_package(self):

        self.assertEqual(
            resolve_relative_name('package', 'package', '.a'),
            'package.a',
        )
        
        self.assertEqual(
            resolve_relative_name('package.sub', 'package.sub', '.a'),
            'package.sub.a',
        )

        self.assertEqual(
            resolve_relative_name('package.sub', 'package.sub', '..a'),
            'package.a',
        )
