"""Strips trailing whitespace off of source files."""

import os
import sys


def main():
    for arg in sys.argv[1:]:
        for dir_name, dir_names, file_names in os.walk(arg):
            dir_names[:] = [x for x in dir_names if not x.startswith('.')]
            file_names = [x for x in file_names if x.endswith('.py') and not x.startswith('.')]
            for file_name in file_names:
                path = os.path.join(dir_name, file_name)
                print path
                source = open(path).read()
                source = source.rstrip() + '\n\n'
                open(path, 'w').write(source)


if __name__ == '__main__':
    main()

