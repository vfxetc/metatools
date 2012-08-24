"""This module deals with finding absolute paths to executables or apps to run.
It is imperative that we return absolute paths so that the executables will be
able to bootstrap a proper development environment.

"""

import os


def get_executable_path(name):
    """Find an executable on the current $PATH.
    
    :param str name: The name of the executable to find.
    :throws ValueError: When it cannot find an executable.
    
    >>> get_executable_path('toolbox')
    <snip $KS_TOOLS>/key_base/bin/generated/toolbox
    
    """
    for dir in os.environ['PATH'].split(':'):
        path = os.path.join(dir, name)
        if os.path.exists(path):
            return path
    raise ValueError('could not find executable %r' % name)


def get_app_or_executable_cmd(app_name, exec_name=None):
    """Find an OS X app (if on a Mac), and fall back to an executable.
    
    :param str app_name: The name of the OS X application to find (without ``.app``).
    :param str exec_name: The name of the executable to find; defaults to ``app_name``.
    :throws ValueError: When it cannot find an app or executable.
    :returns: A list that is directly usable in :class:`subprocess.Popen`, and which
    anything appended to will be treated as an argument.
    
    On a Mac when there is an application:
    
    >>> get_app_or_executable_cmd('qb-reelsmart', 'qb_reelsmart')
    ['open', '<snip $KS_TOOLS>/key_base/qb-reelsmart.app', '--args']
    
    On Linux, or when there is no application:
    
    >>> get_app_or_executable_cmd('qb-reelsmart', 'qb_reelsmart')
    ['<snip $KS_TOOLS>/key_base/bin/generated/qb_reelsmart']
    
    """
    
    # Prioritize applications on OS X
    if os.uname()[0] == "Darwin":
        tools_paths = os.environ.get('KS_PYTHON_SITES', '').split(':')
        tools_paths.append(os.environ['KS_TOOLS'])
        for tools_path in tools_paths:
            app_path = os.path.join(tools_path, 'key_base', 'applications', app_name + '.app')
            if os.path.exists(app_path):
                return ['open', app_path, '--args']
    
    # Default to looking for an executable.
    return [get_executable_path(exec_name or app_name)]


if __name__ == '__main__':
    
    import optparse
    optparser = optparse.OptionParser()
    optparser.add_option('-a', '--app', dest="app", action="store_true", default=False)
    opts, args = optparser.parse_args()
    
    if opts.app:
        print get_app_or_executable_cmd(*args)
    else:
        print get_executable_path(*args)

