import subprocess
import re
import os
import sys

changed = set()

def call_output(cmd, stdin=None):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    return proc.communicate(stdin or '')[0]

# Collect all of the files which have been changed.
for line in sys.stdin:
    old_sha, new_sha, new_name = line.strip().split()
    proc = subprocess.Popen(['git', 'diff', '--name-only', old_sha, new_sha],
        stdout=subprocess.PIPE)
    filenames = [x.strip() for x in proc.stdout if x.strip().endswith('.py')]

    print 'PyFlakes for %s:' % new_name
    for filename in sorted(filenames):

        print '\t%s' % filename

        old_src = call_output(['git', 'cat-file', 'blob', '%s:%s' % (old_sha, filename)])
        new_src = call_output(['git', 'cat-file', 'blob', '%s:%s' % (new_sha, filename)])

        old_flakes = call_output(['pyflakes'], old_src)
        new_flakes = call_output(['pyflakes'], new_src)
        print old_flakes.strip()
        print new_flakes.strip()



