from common import *

from metatools.imports.rewrite import rewrite


class TestImportRewrites(TestCase):

    def assertRewrite(self, original, target, changes, module_name=None, *args):
        new = rewrite(original, changes, module_name)
        self.assertEqual(new, target, *args)

    def test_passthrough(self):
        src = dedent('''
            import a.b.c
            from a import b
            a.a_func()
            a.b.b_func()
        ''')
        self.assertRewrite(src, src, {})

    def test_direct_singles(self):
        self.assertRewrite(dedent('''
            import a
        '''), dedent('''
            import x
        '''), {
            'a': 'x',
        })

    def test_direct_single_with_use(self):
        self.assertRewrite(dedent('''
            import a
            a.func()
        '''), dedent('''
            import x
            x.func()
        '''), {
            'a': 'x',
        })

    def test_import_func_from_single(self):
        self.assertRewrite(dedent('''
            from a import func
        '''), dedent('''
            from x import func
        '''), {
            'a': 'x',
        })

    def test_import_mod_from_single(self):
        self.assertRewrite(dedent('''
            from a import b
        '''), dedent('''
            from x import y
        '''), {
            'a.b': 'x.y',
        })

    def test_import_relative(self):
        self.assertRewrite(dedent('''
            from . import c
        '''), dedent('''
            from a.b import x
        '''), {
            'a.b.c': 'a.b.x',
        },
            'a.b.mod',
        )

