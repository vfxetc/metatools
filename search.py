import os


def get_executable_path(name):
    """Find an executable on the current $PATH."""
    for dir in os.environ['PATH'].split(':'):
        path = os.path.join(dir, name)
        if os.path.exists(path):
            return path
    raise ValueError('could not find executable %r' % name)


def get_app_or_executable_cmd(app_name, exec_name=None):
    """Find an OS X app (if on a Mac), and fall back to an executable.
    
    Returns a list that is directly usable in :class:`subprocess.Popen`, and which
    anything appended to will be treated as an argument.
    
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

