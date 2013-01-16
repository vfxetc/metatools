from __future__ import print_function

import sys
import re
import optparse
import os
import token
import itertools
import lib2to3.pgen2.tokenize
import lib2to3.pygram
import lib2to3.pytree
import hashlib
import difflib
import traceback
from cStringIO import StringIO


def diff_texts(a, b, filename):
    """Return a unified diff of two strings."""
    a = a.splitlines()
    b = b.splitlines()
    return '\n'.join(difflib.unified_diff(
        a, b,
        filename, filename,
        "(original)", "(refactored)",
        lineterm="",
    ))


def module_name_for_path(path):
    head, module = os.path.split(os.path.splitext(path)[0])
    while os.path.exists(os.path.join(head, '__init__.py')):
        head, tail = os.path.split(head)
        module = tail + '.' + module

    # key_base pseudopackages; only the few that the external tools are
    # in.
    if '/key_base/' in head:
        if '/maya/python/' in head:
            return 'ks.maya.' + module
        if '/key_base/python/' in head:
            return 'ks.' + module

    return module


def resolve_relative(relative, module):

    if not relative.startswith('.'):
        return 0, relative

    orig_relative = relative
    parts = module.split('.')

    while relative.startswith('.'):
        relative = relative[1:]
        parts.pop(-1)
    parts.append(relative)
    
    return len(orig_relative) - len(relative), '.'.join(x for x in parts if x)


def _iter_chunked_source(source):
    driver = lib2to3.pgen2.driver.Driver(lib2to3.pygram.python_grammar, lib2to3.pytree.convert)
    
    if hasattr(lib2to3.pgen2.tokenize, 'detect_encoding'):
        encoding, _ = lib2to3.pgen2.tokenize.detect_encoding(string_io.readline)
        string_io = StringIO(source)
    else:
        encoding = 'utf8'

    tree = driver.parse_string(source)
    for is_source, group in itertools.groupby(_iter_chunked_node(tree), lambda (is_source, _): is_source):
        yield is_source, ''.join((value.encode(encoding) if isinstance(value, unicode) else value) for _, value in group)


def _iter_chunked_node(node):

    if isinstance(node, lib2to3.pytree.Node):
        for child in node.children:
            for chunk in _iter_chunked_node(child):
                yield chunk

    else:
        
        # Deal with comments and spaces; comments -> False
        prefix = node.prefix or ''
        yield (not prefix.strip().startswith('#')), prefix

        # Everything that isn't a STRING can have identifiers.
        yield (node.type not in (token.STRING, )), node.value


def rewrite(source, mapping, module_name=None, non_source=False):

    rewriter = Rewriter(mapping, module_name)

    if non_source:
        return rewriter(source)

    rewritten = []

    # Break the source into chunks that we may find identifiers in, and those
    # that we won't.
    for is_source, source in _iter_chunked_source(source):

        # Don't bother looking in comments and strings.
        if is_source:
            rewritten.append(rewriter(source))
        else:
            rewritten.append(source)

    return ''.join(rewritten)


class Rewriter(object):

    _direct_import_re = re.compile(r'''
        import\s+
        (
            (?:
                (?:,\s*)? # Splitting consecutive imports.
                [\w\.]+ # The thing being imported.
                (?:\s+as\s+\w+\s*?)? # It's new name.
            | \*
            )+
        )
    ''', re.X)

    _import_from_re = re.compile(r'''
        from\s+
        ([\w\.]+)\s+
        import\s+
        (
            (?:
                (?:,\s*)? # Splitting consecutive imports.
                \w+ # The thing being imported.
                (?:\s+as\s+\w+\s*?)? # It's new name.
            | \*
            )+
        )
    ''', re.X)

    _usage_re = re.compile(r'''
        [a-zA-Z_][a-zA-Z_0-9]*
        (:?.[a-zA-Z_][a-zA-Z_0-9]*)*
    ''', re.X)

    def __init__(self, mapping, module_name):

        self.mapping = mapping
        self.module_name = module_name
        self.substitutions = {}

    def __call__(self, source):

        source = self._import_from_re.sub(self.import_from, source)
        source = self._direct_import_re.sub(self.direct_import, source)
        source = self._usage_re.sub(self.usage, source)

        for from_, to in self.substitutions.iteritems():
            source = source.replace(from_, to)

        return source

    def add_substitution(self, source):
        tag = '__%s__' % hashlib.md5(source).hexdigest()
        self.substitutions[tag] = source
        return tag

    def split_as_block(self, block):
        for chunk in block.split(','):
            name, as_ = (re.split(r'\s+as\s+', chunk) + [None])[:2]
            name = name.strip()
            as_ = as_ and as_.strip()
            yield name, as_

    def import_from(self, m):

        # print 'import_from:', m.groups()
        was_relative, base = resolve_relative(m.group(1), self.module_name)

        imports = []

        # Convert the full names of every item.
        for name, ident in self.split_as_block(m.group(2)):
            full_name = base + '.' + name
            imports.append((
                self.convert_module(full_name) or full_name,
                ident,
            ))
        
        # Assert that every item shares the same prefix.
        new_base = imports[0][0].split('.')[:-1]
        if any(x[0].split('.')[:-1] != new_base for x in imports[1:]):
            raise ValueError('conflicting rewrites in single import')

        # Restore the relative levels.
        if was_relative:
            new_base = self.make_relative(new_base)
        else:
            new_base = '.'.join(new_base)

        # Rebuild the "as" block.
        imports = [(name.split('.')[-1], ident) for name, ident in imports]
        imports = [('%s as %s' % (name, ident) if ident else name) for name, ident in imports]

        # Format the final source.
        return self.add_substitution('from %s import %s' % (
            new_base,
            ', '.join(imports)
        ))

    def make_relative(self, target):
        base = (self.convert_module(self.module_name) or self.module_name).split('.')
        while target and base and target[0] == base[0]:
            target = target[1:]
            base = base[1:]
        return '.' * len(base) + '.'.join(target)

    def direct_import(self, m):
        # print 'direct_import:', m.groups()

        imports = []

        # Convert the full names of every item.
        for name, ident in self.split_as_block(m.group(1)):
            imports.append((
                self.convert_module(name) or name,
                ident,
            ))

        # Rebuild the "as" block.
        imports = [('%s as %s' % (name, ident) if ident else name) for name, ident in imports]

        # Format the final source.
        return self.add_substitution('import ' + ', '.join(imports))

    def usage(self, m):
        # print 'usage:', m.group(0)
        name = m.group(0)
        name = self.convert_identifier(name) or name
        return name

    def convert_module(self, name):
        parts = name.split('.')
        for old, new in self.mapping.iteritems():
            old_parts = old.split('.')
            if parts[:len(old_parts)] == old_parts:
                return '.'.join([new] + parts[len(old_parts):])

    def convert_identifier(self, name):
        parts = name.split('.')
        for old, new in self.mapping.iteritems():
            old_parts = old.split('.')
            if parts[:len(old_parts)] == old_parts:
                return '.'.join([new] + parts[len(old_parts):])




def main():

    opt_parser = optparse.OptionParser(usage="%prog [options] from:to... path...")
    opt_parser.add_option('-w', '--write', action='store_true')
    opts, args = opt_parser.parse_args()

    renames = []
    for i, arg in enumerate(args):
        if ':' not in arg:
            break
        old, new = arg.split(':', 1)
        renames.append((old, new))
    args = args[i:]

    if not renames or not args:
        opt_parser.print_usage()
        exit(1)

    visited_paths = set()
    changed = set()

    def process(dir_name, path):

        if path.startswith('._') or not path.endswith('.py'):
            return

        if dir_name is not None:
            path = os.path.join(dir_name, path)

        if path in visited_paths:
            return
        visited_paths.add(path)

        print('#', path, file=sys.stderr)

        module_name = module_name_for_path(path)
        original = open(path).read().rstrip() + '\n'
        refactored = rewrite(original, dict(renames), module_name)

        if re.sub(r'\s+', '', refactored) != re.sub(r'\s+', '', original):
            print(diff_texts(original, refactored, path))
            if opts.write:
                with open(path, 'wb') as fh:
                    fh.write(refactored)

    for arg in args:

        try:
            process(None, arg)
        except Exception:
            print('# ERROR during', arg, file=sys.stderr)
            traceback.print_exc()

        for dir_name, dir_names, file_names in os.walk(arg):
            dir_names[:] = [x for x in dir_names if not x.startswith('.')]
            for file_name in file_names:
                try:
                    process(dir_name, file_name)
                except Exception:
                    print('# ERROR during', os.path.join(dir_name, file_name), file=sys.stderr)
                    traceback.print_exc()

    print('Modified (%d)' % len(changed), file=sys.stderr)
    print('\n'.join(sorted(changed)), file=sys.stderr)


if __name__ == '__main__':
    main()

