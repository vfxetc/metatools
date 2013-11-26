import os
import sys
import optparse
import fnmatch

from .discovery import parse_imports
from .utils import get_name_for_path


def iter_modules(root):
    for dir_name, dir_names, file_names in os.walk(root):
        module_paths = [os.path.join(dir_name, x) for x in file_names if x.endswith('.py')]
        for path in module_paths:

            module = get_name_for_path(path)
            package = module.rsplit('.', 1)[0]

            if module.rsplit('.', 1)[-1] == '__init__':
                module = package

            yield path, module, parse_imports(open(path).read(), package, module, path, toplevel=False)


def iter_dot(opts, roots):

    # Parse everything.
    all_modules = {}
    packages = set()
    for root in roots:
        for path, module, imports in iter_modules(root):
            all_modules[module] = set(imports)
            if os.path.basename(path) == '__init__.py':
                packages.add(module)

    # Filter them to exclude patterns.
    all_modules = dict(
        (name, imports)
        for name, imports in all_modules.iteritems()
        if not any(fnmatch.fnmatch(name, pattern) for pattern in opts.exclude or [])
    )

    # Filter the imports to things that we have found.
    for module, imports in all_modules.iteritems():
        imports.intersection_update(x for x in imports if x in all_modules)


    # Output the graph.
    yield 'digraph {'

    levels = []
    for module, imports in all_modules.iteritems():

        # Collect everything that is the same level.
        level = module.count('.')
        while len(levels) <= level:
            levels.append([])
        levels[level].append(module)

        # Fill packages.
        if module in packages and (imports or opts.implied):
            yield '\t"%s" [style=filled]' % module

        for import_ in set(imports):

            m_parts = module.split('.')
            i_parts = import_.split('.')
            if m_parts[:len(i_parts)] == i_parts:
                imports.remove(import_)
                continue

            constrain = i_parts[:len(m_parts)] == m_parts
            yield '\t"%s" -> "%s" [%s]' % (module, import_, 'constraint=false' if not constrain else '')

    # Parent links.
    if opts.implied:
        for module, imports in all_modules.iteritems():
            parent = module.rsplit('.', 1)[0]
            if parent != module and parent not in imports and module not in all_modules.get(parent, []):
                yield '\t"%s" -> "%s" [style=dotted]' % (parent, module)

    # for level, modules in enumerate(levels):
    #     if modules:
    #         yield '\t{rank=same; %s}' % (' '.join('"%s"' % x for x in modules))

    yield '}'


def main():

    optparser = optparse.OptionParser()
    optparser.add_option('-e', '--exclude', action='append')
    optparser.add_option('-x', '--explicit', action='store_false', dest='implied')
    opts, args = optparser.parse_args()

    print '\n'.join(iter_dot(opts, args))


if __name__ == '__main__':
    main()


