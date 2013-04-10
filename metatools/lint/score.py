"""Strips trailing whitespace off of source files."""

import os
import re
import sys
from subprocess import Popen, PIPE, call

import pylint.lint
import pylint.reporters


class _NullReporter(pylint.reporters.BaseReporter):
    def add_message(*args):
        pass
    def _display(*args):
        pass


def score_path(path):

    linter = pylint.lint.PyLinter()
    linter.load_default_plugins()
    linter.reporter = _NullReporter()
    linter.check([path])
    return eval(linter.config.evaluation, {}, linter.stats)


def main():

    data = []

    for arg in sys.argv[1:]:
        for dir_name, dir_names, file_names in os.walk(arg):
            dir_names[:] = [x for x in dir_names if not x.startswith('.')]
            file_names = [x for x in file_names if x.endswith('.py') and not x.startswith('.')]
            for file_name in file_names:

                path = os.path.join(dir_name, file_name)
                try:
                    score = score_path(path)
                except:
                    score = 0.0
                print '%.3f %s' % (score, path)
                data.append((score, path))

    print

    hist = [0] * 11
    data.sort()
    for score, path in data:
        print '%.3f %s' % (score, path)

        if not score:
            continue

        score = min(10, max(0, int(round(score))))
        hist[score] += 1


    print ' '.join(str(x) for x in hist)

    chart_url = re.sub(r'\s+', '', '''http://chart.googleapis.com/chart
        ?chxt=y
        &chbh=a,2
        &chs=400x100
        &cht=bvg
        &chco=A2C180

        &chxr=0,0,%d
        &chds=0,10
        &chd=t:%s

    ''' % (
        max(hist),
        ','.join(str(x) for x in hist),
    ))
    call(['open', chart_url])

if __name__ == '__main__':
    main()

