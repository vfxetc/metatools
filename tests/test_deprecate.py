import warnings

from common import *

from metatools.deprecate import *


class TestRenamedModule(TestCase):

    def setUp(self):
        self.module_sandbox = os.path.splitext(__file__)[0] + '_sandbox'
        if self.module_sandbox not in sys.path:
            sys.path.insert(0, self.module_sandbox)

    def tearDown(self):
        if sys.path[0] == self.module_sandbox:
            sys.path.pop(0)

    def test_absolute(self):

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            import test_dep_use

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, ModuleRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'test_dep_old was renamed to test_dep_new')
        self.assertEqual(test_dep_use.func(1, 2), 3)

    def test_relative(self):

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            import test_dep_pack.use

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, ModuleRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'test_dep_pack.old was renamed to test_dep_pack.new')
        self.assertEqual(test_dep_pack.use.func(1, 2), 3)


class TestRenamedAttribute(TestCase):

    def test_instance_value(self):

        class Example(object):

            def __init__(self):
                self.new = 1

            old = renamed_attr('new')

        e = Example()

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(1, e.old)
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, AttributeRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'Example.old was renamed to new')

        with warnings.catch_warnings(record=True) as w:
            e.old = 2
            self.assertEqual(2, e.new)
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, AttributeRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'Example.old was renamed to new')

    def test_class_value(self):

        class Example(object):
            new = 1
            old = renamed_attr('new')

        e = Example()

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(1, Example.old)
            self.assertEqual(1, e.old)
        self.assertEqual(len(w), 2)
        self.assertTrue(issubclass(w[0].category, AttributeRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'Example.old was renamed to new')

        with warnings.catch_warnings(record=True) as w:
            e.old = 2
            self.assertEqual(2, e.new)
            self.assertEqual(1, Example.old)
            self.assertEqual(1, Example.new)
        self.assertEqual(len(w), 2)
        self.assertTrue(issubclass(w[0].category, AttributeRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'Example.old was renamed to new')

    def test_instance_method(self):

        class Example(object):

            def new(self, a, b):
                return a + b

            old = renamed_attr('new')

        e = Example()

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(3, e.old(1, 2))
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, AttributeRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'Example.old was renamed to new')


class TestRenamedFunction(TestCase):

    def test_renamed_func(self):

        def new(a, b):
            return a + b
        old = renamed_func(new, 'old', __name__)

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(3, old(1, 2))
        self.assertEqual(1, len(w))
        self.assertTrue(issubclass(w[0].category, FunctionRenamedWarning))
        self.assertEqual(w[0].message.args[0], 'test_deprecate.old was renamed to test_deprecate.new')


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
