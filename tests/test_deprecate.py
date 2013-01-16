import sys
import os
import warnings

from common import *

from metatools import deprecate


class TestRenamedModule(TestCase):

    def setUp(self):
        self.module_sandbox = os.path.splitext(__file__)[0] + '_sandbox'
        sys.path.insert(0, self.module_sandbox)

    def tearDown(self):
        if sys.path[0] == self.module_sandbox:
            sys.path.pop(0)

    def test(self):

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            import dep_use

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, deprecate.ModuleRenamedWarning))
        self.assertEqual(dep_use.func(1, 2), 3)

