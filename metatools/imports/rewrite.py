import re
import optparse
import os
import functools
import token
import itertools
import lib2to3.pgen2
import lib2to3.pygram
import lib2to3.pytree
import hashlib


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
    tree = driver.parse_string(source)
    for is_source, group in itertools.groupby(_iter_chunked_node(tree), lambda (is_source, _): is_source):
        yield is_source, ''.join(value for _, value in group)


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

        # print ('#' if not is_source else ' '), unicode(source).encode('unicode-escape')

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
            (?:,\s*)? # Splitting consecutive imports.
            [\w\.]+ # The thing being imported.
            (?:\s+as\s+\w+\s*?)? # It's new name.
        )
    ''', re.X)

    _import_from_re = re.compile(r'''
        from\s+
        ([\w\.]+)\s+
        import\s+
        (
            (?:,\s*)? # Splitting consecutive imports.
            [\w\.]+ # The thing being imported.
            (?:\s+as\s+\w+\s*?)? # It's new name.
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

    def import_from(self, m):
        print 'import_from:', m.groups()

        source = m.group(0)
        return self.add_substitution(source)

    def direct_import(self, m):
        print 'direct_import:', m.groups()

        chunks = []
        for chunk in m.group(1).split(','):

            name, as_ = (chunk.split('as') + [None])[:2]
            name = name.strip()
            as_ = as_ and as_.strip()

            new_name = self.convert_module(name) or name
            chunks.append(' as '.join(filter(None, [new_name, as_])))

        return self.add_substitution('import ' + ', '.join(chunks))

    def usage(self, m):
        print 'usage:', m.group(0)

        name = m.group(0)
        name = self.convert_identifier(name) or name

        return name

    def convert_module(self, name):
        parts = name.split('.')
        for old, new in self.mapping.iteritems():
            old_parts = old.split('.')
            if parts[:len(old_parts)] == old_parts:
                # self.fixed_count += 1
                return '.'.join([new] + parts[len(old_parts):])

    def convert_identifier(self, name):
        parts = name.split('.')
        for old, new in self.mapping.iteritems():
            old_parts = old.split('.')
            if parts[:len(old_parts)] == old_parts:
                # self.fixed_count += 1
                return '.'.join([new] + parts[len(old_parts):])




def main():

    opt_parser = optparse.OptionParser(usage="%prog from:to... path...")
    opt_parser.add_option('-n', '--dry-run', dest='dry_run', action='store_true', default=False)
    opt_parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False)
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







    class Fixer(object):

        def __init__(self, module_name):
            self.module_name = module_name
            self.fixed_count = 0

        def absolute(self, m):
            name = m.group(2)
            conv = self.convert(name)
            if conv is not None:
                print '\tabs: %s -> %s' % (name, conv)
                return '%s%s%s' % (m.group(1), conv, m.group(3))
            return m.group(0)

        def relative(self, m):
            name = m.group(2)
            try:
                levels, abs_name = resolve_relative(name, self.module_name)
            except IndexError:
                return m.group(0)
            conv = self.convert(abs_name)
            if conv is not None:
                if levels:
                    target = conv.split('.')
                    base = (self.convert(self.module_name) or self.module_name).split('.')
                    while target and base and target[0] == base[0]:
                        target = target[1:]
                        base = base[1:]
                    conv = '.' * len(base) + '.'.join(target)
                print '\trel: %s -> %s' % (name, conv)
                return '%s%s%s' % (m.group(1), conv, m.group(3))
            return m.group(0)



    visited_paths = set()

    def process(dir_name, path):

        if path.startswith('._') or not path.endswith('.py'):
            return

        if dir_name is not None:
            path = os.path.join(dir_name, path)

        if path in visited_paths:
            return
        visited_paths.add(path)

        module_name = module_name_for_path(path)
        print '%s (%s)' % (module_name, path)

        fixer = Fixer(module_name)
        source = open(path).read()
        source, abs_count = absolute_re.subn(fixer.absolute, source)
        source, rel_count = relative_re.subn(fixer.relative, source)
        if fixer.fixed_count and not opts.dry_run:
            open(path, 'w').write(source)


    for arg in args:
        process(None, arg)
        for dir_name, dir_names, file_names in os.walk(arg):
            dir_names[:] = [x for x in dir_names if not x.startswith('.')]
            for file_name in file_names:
                process(dir_name, file_name)

