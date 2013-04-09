"""Rewrites several uses of `platform.system()` into ``sys.platform``."""

import os
import sys
import re


direct_re = re.compile(r'''

    (?:
        platform\.system \s* \(\s*\) |
        os\.uname \s* \(\s*\) \s* \[\s*0\s*\]
    )
    \s*==\s*
    [rRuUbB]?['"]+(Darwin|Linux|Windows)['"]+

''', re.VERBOSE)


def direct_replace(m):
    return 'sys.platform.startswith("%s")' % {
        "Darwin": "darwin",
        "Linux": "linux",
        "Windows": "win32",
    }[m.group(1)]


def main():

    for arg in sys.argv[1:]:
        for dir_name, dir_names, file_names in os.walk(arg):

            # Filter dotted paths out.
            dir_names[:] = [x for x in dir_names if not x.startswith('.')]

            file_names = [x for x in file_names if x.endswith('.py') and not x.startswith('.')]
            for file_name in file_names:

                path = os.path.join(dir_name, file_name)
                with open(path) as fh:
                    source = fh.read()

                source, count = direct_re.subn(direct_replace, source)
                if count:

                    print path

                    # Make sure it has a "import sys" at the top.
                    m = re.search(r'^import sys', source, re.MULTILINE)
                    if not m:

                        # Put it before the os OR platform import.
                        m = re.search(r'^import (os|platform)', source, re.MULTILINE)

                        if not m:
                            print '\tNo platform import; cannot auto import sys!'
                            continue

                        source = source[:m.start(0)] + 'import sys\n' + source[m.start(0):]

                    with open(path, 'wb') as fh:
                        fh.write(source)


if __name__ == '__main__':
    main()

