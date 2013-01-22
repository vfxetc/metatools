import sys
import os
import warnings

from common import *

from metatools import back_compat


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
            import test_bc_use

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, back_compat.ModuleRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'test_bc_old was renamed to test_bc_new')
        self.assertEqual(test_bc_use.func(1, 2), 3)


class TestFunctionDecorator(TestCase):

    def test(self):

        @back_compat.decorate
        def func(a, b):
            return a + b

        with warnings.catch_warnings(record=True) as w:
            namespace = {'func': func}
            eval(compile('\n\nres = func(1, 2)', '<string>', 'exec'), namespace)
            self.assertEqual(namespace['res'], 3)

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, back_compat.FunctionDeprecatedWarning))
        self.assertEqual(w[0].message.args[0], 'func has been deprecated')
        self.assertEqual(w[0].lineno, 3)
        self.assertEqual(w[0].filename, '<string>')
