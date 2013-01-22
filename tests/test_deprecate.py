import warnings

from common import *

from metatools.deprecate import deprecate, CallingDeprecatedWarning


class TestFunctionDecorator(TestCase):

    def test(self):

        @deprecate
        def func(a, b):
            return a + b

        with warnings.catch_warnings(record=True) as w:
            namespace = {'func': func}
            eval(compile('\n\nres = func(1, 2)', '<string>', 'exec'), namespace)
            self.assertEqual(namespace['res'], 3)

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, CallingDeprecatedWarning))
        self.assertEqual(w[0].message.args[0], 'Calling test_deprecate.func has been deprecated')
        self.assertEqual(w[0].lineno, 3)
        self.assertEqual(w[0].filename, '<string>')
