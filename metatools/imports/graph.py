import os
import sys
import optparse

from .discovery import parse_toplevel_imports
from .utils import get_name_for_path


def iter_modules(root):
    for dir_name, dir_names, file_names in os.walk(root):
        module_paths = [os.path.join(dir_name, x) for x in file_names if x.endswith('.py')]
        for path in module_paths:

            module = get_name_for_path(path)
            package = module.rsplit('.', 1)[0]

            if module.rsplit('.', 1)[-1] == '__init__':
                module = package

            yield path, module, parse_toplevel_imports(open(path).read(), package, module)

def main():

    optparser = optparse.OptionParser()
    opts, args = optparser.parse_args()

    # Parse everything.
    all_modules = {}
    packages = set()
    for path, module, imports in iter_modules(args[0]):
        all_modules[module] = imports
        if os.path.basename(path) == '__init__.py':
            packages.add(module)

    # Filter the imports to things that we have found.
    for module, imports in all_modules.iteritems():
        imports[:] = [x for x in imports if x in all_modules]

    # Output the graph.
    print 'digraph "%s" {' % args[0]
    levels = []
    for module, imports in all_modules.iteritems():

        # Collect everything that is the same level.
        level = module.count('.')
        while len(levels) <= level:
            levels.append([])
        levels[level].append(module)

        # Fill packages.
        if module in packages:
            print sys.stderr, '\t"%s" [style=filled]' % module

        for import_ in imports:

            m_parts = module.split('.')
            i_parts = import_.split('.')
            if m_parts[:len(i_parts)] == i_parts:
                continue

            print '\t"%s" -> "%s" [%s]' % (module, import_, 'constraint=false' if module.count('.') >= import_.count('.') else '')

    # Parent links.
    for module, imports in all_modules.iteritems():
        parent = module.rsplit('.', 1)[0]
        if parent != module and parent not in imports and module not in all_modules.get(parent, []):
            print '\t"%s" -> "%s" [style=dotted]' % (parent, module)

    for level, modules in enumerate(levels):
        if modules:
            print '\t{rank=same; %s}' % (' '.join('"%s"' % x for x in modules))

    print '}'



if __name__ == '__main__':
    main()


