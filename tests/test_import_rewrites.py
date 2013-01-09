from common import *

from metatools.imports.rewrite import rewrite


class TestImportRewrites(TestCase):

    def assertRewrite(self, original, target, changes, *args):
        new = rewrite(original, changes)
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

    def _test_direct_as_single_with_use(self):
        self.assertRewrite(dedent('''
            import old as mod
            old.func()
            mod.func()
        '''), dedent('''
            import new as mod
            old.func()
            mod.func()
        '''), {
            'old': 'new',
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

