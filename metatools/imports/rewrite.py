import re
import optparse
import os
import functools


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


absolute_re = re.compile(r'(import\s+)([\w\.]+)(\s+)')
relative_re = re.compile(r'(from\s+)([\w\.]+)(\s+import)')


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


def resolve_relative(orig_relative, module):
    relative = orig_relative
    parts = module.split('.')
    if not relative.startswith('.'):
        return len(orig_relative) - len(relative), relative
    while relative.startswith('.'):
        relative = relative[1:]
        parts.pop(-1)
    parts.append(relative)
    return len(orig_relative) - len(relative), '.'.join(x for x in parts if x)


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

    def convert(self, name):
        parts = name.split('.')
        for old, new in renames:
            old_parts = old.split('.')
            if parts[:len(old_parts)] == old_parts:
                self.fixed_count += 1
                return '.'.join([new] + parts[len(old_parts):])


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

