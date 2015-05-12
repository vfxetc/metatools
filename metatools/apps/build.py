from distutils import sysconfig
from distutils.ccompiler import new_compiler
from subprocess import call, check_call
import argparse
import datetime
import glob
import os
import re
import shutil
import sys
import tempfile

import yaml


from metatools.utils import dedent




def compile_bootstrap(target, source):

    get_var = sysconfig.get_config_var

    cc = new_compiler(verbose=1)

    c_flags = ['-I' + sysconfig.get_python_inc(), '-I' + sysconfig.get_python_inc(plat_specific=True)]
    c_flags.extend(get_var('CFLAGS').split())

    ld_flags = get_var('LIBS').split() + get_var('SYSLIBS').split()
    ld_flags.append('-lpython' + get_var('VERSION'))
    if not get_var('Py_ENABLE_SHARED'):
        ld_flags.insert(0, '-L' + get_var('LIBPL'))
    if not get_var('PYTHONFRAMEWORK'):
        ld_flags.extend(get_var('LINKFORSHARED').split())

    c_source_path = os.path.abspath(os.path.join(__file__, '..', 'bootstrap.c'))
    build_dir = tempfile.mkdtemp(prefix='metatools_app.%s.' % os.path.basename(target))
    objs = cc.compile([c_source_path], build_dir, extra_preargs=c_flags,
        macros=[('METATOOLS_BOOTSTRAP_SOURCE', '"%s"' % source.encode('string-escape'))],
    )
    cc.link(cc.EXECUTABLE, objs, target, extra_preargs=ld_flags)

    shutil.rmtree(build_dir)


def main():

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-f', '--force', action='store_true')
    arg_parser.add_argument('--icons', action='append')
    arg_parser.add_argument('app_yaml')
    arg_parser.add_argument('build_dir')

    build_time = datetime.datetime.now()
    absolute_self = os.path.abspath(__file__)

    # These two are dependant on the WesternX Python environment.
    local_tools = os.path.abspath(os.path.join(__file__, '..', '..', '..'))
    icons_dir = os.path.join(local_tools, 'key_base', '2d', 'icons')
    
    # dev dir doesn't exist use network build location
    if not os.path.exists(icons_dir):
        local_tools = os.path.abspath(os.path.join(__file__, '..', '..', '..', '..', '..'))
        icons_dir = os.path.join(local_tools, 'key_base', '2d', 'icons')

    args = sys.argv[1:]


    for cfg_file in args:    
        config = yaml.load(open(cfg_file).read()) or {}


        # Get a name, or use the name of the config file.
        name = config.get('name') or os.path.basename(cfg_file)[:-4]
        safe_name = re.sub(r'\W+', '_', name)
        print '\t' + name + '.app'
        
        # Get the icon, or look for one that matches the name.
        icon = config.get('icon') or name + '.icns'
        icon = os.path.join(icons_dir, icon)
        icon = icon if os.path.exists(icon) else None
        
        # Get the command, defaulting to the name.
        command = config.get('command')
        entrypoint = config.get('entrypoint')
        if entrypoint:
            entrypoint = entrypoint.split(':')
            if len(entrypoint) > 2:
                print 'ERROR: entrypoint must be "package.module" or "package.module:function"'
                continue
        else:
            command = safe_name

                # Clean up the old one.
        if os.path.exists(bundle_path):
            for name in os.listdir(bundle_path):
                call(['rm', '-rf', os.path.join(bundle_path, name)])


def build_one(bundle_path, name=None, command=None, entrypoint=None, execfile=None,
    icon=None, profile=True, compile=False, identifier=None, version='1.0.0'):

    if not bundle_path.endswith('.app'):
        raise ValueError('bundle_path must end in .app')

    if entrypoint:
        entrypoint = entrypoint.split(':')
        if len(entrypoint) > 2:
            raise ValueError('entrypoint must be "package.module" or "package.module:function"')
    elif command:
        if compile:
            raise ValueError('cannot compile bootstrap for external command')
    elif execfile:
        pass
    else:
        raise ValueError('requires either command or entrypoint')

    if name is None:
        name = os.path.splitext(os.path.basename(bundle_path))[0]
    safe_name = re.sub(r'\W+', '_', name)

    if identifier is None:
        identifier = 'com.keypics.%s' % safe_name

    # Make sure we have an empty bundle.
    if os.path.exists(bundle_path) and os.listdir(bundle_path):
        raise ValueError('bundle_path exists: %s' % bundle_path)
    os.makedirs(os.path.join(bundle_path, 'Contents', 'MacOS'))

    # Copy in an icon.
    if icon:
        os.makedirs(os.path.join(bundle_path, 'Contents', 'Resources'))
        shutil.copy(icon, os.path.join(bundle_path, 'Contents', 'Resources'))
    
    # Build the plist
    plist = {}
    plist['CFBundleDisplayName'] = safe_name
    plist['CFBundleIdentifier'] = identifier
    plist['CFBundleVersion'] = version
    plist['CFBundleExecutable'] = ('bootstrap_' if compile else '') + safe_name
    if icon:
        plist['CFBundleIconFile'] = os.path.basename(icon)
    
    with open(os.path.join(bundle_path, 'Contents', 'Info.plist'), 'w') as fh:
        fh.write(dedent('''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
        '''))
        for k, v in plist.items():
            fh.write('\t<key>%s</key>\n' % k)
            fh.write('\t<string>%s</string>\n' % v)
        fh.write('</dict>\n</plist>\n')
    
    # Build the launcher.

    if profile or not compile:
        target = os.path.join(bundle_path, 'Contents', 'MacOS', ('bootstrap_' if compile else '') + safe_name)
        absolute_self = os.path.abspath(__file__)
        build_time = datetime.datetime.now()
        with open(target, 'w') as fh:

            fh.write(dedent('''#!/bin/bash

                # This file was automatically generated by
                # %(absolute_self)s
                # at %(build_time)s.

                # Remove OS X's automatic Process Serial Number. There is apparently no way for
                # us to detect if this will be passed beyond simply looking for it, so make sure
                # that you don't `open` one of these apps and pass it a single argument that
                # starts with "-psn", or it will be removed.
                if [[ "$#" == 1 && "${1:0:4}" == "-psn" ]]; then
                    shift
                fi

            ''' % locals()))

            if profile:
                fh.write(dedent('''

                    # Build the environment if it doesn't already exist. We try to recreate the
                    # bash environment as if invocated with "--login".
                    if [[ "$SHLVL" < 2 ]]; then
                        
                        # Global profile.
                        if [[ -f /etc/profile ]]; then
                            source /etc/profile
                        fi
                        
                        # User profile.
                        for x in ~/.bash_profile ~/.bash_login ~/.profile; do
                            if [[ -f $x ]]; then
                                source $x
                                break
                            fi
                        done

                    fi

                '''))

            if compile:
                fh.write('exec "$(dirname "$0")/%s" "$@"\n' % safe_name)
            elif entrypoint:
                if len(entrypoint) == 1:
                    fh.write('''exec python -c "import sys; sys.argv[0] = '$0'; import %s" "$@"\n''' % (entrypoint[0], ))
                else:
                    fh.write('''exec python -c "import sys; sys.argv[0] = '$0'; import %s as m; m.%s()" "$@"\n''' % (
                        entrypoint[0], entrypoint[1],
                    ))
            elif execfile:
                fh.write('''exec python -c "import sys; sys.argv[0] = '$0'; execfile(%r)\n''' % (execfile, ))
            else:
                fh.write('''exec %s "$@"\n''' % (command, ))

        check_call(['chmod', 'a+x', target])

    if compile:
        target = os.path.join(bundle_path, 'Contents', 'MacOS', safe_name)
        if entrypoint and len(entrypoint) > 1:
            compile_bootstrap(target, dedent('''
                import os
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
                import %s
                %s.%s()
            ''' % (entrypoint[0], entrypoint[1], entrypoint[1])))
        elif entrypoint:
            compile_bootstrap(target, dedent('''
                import os
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
                import %s
                ''' % (entrypoint[0], )))
        else:
            compile_bootstrap(target, dedent('''
                import os
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
                execfile(os.path.join(sys.path[0], %r))
                ''' % (execfile, )))



                
    
    # DONE

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--force', action='store_true')

    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--profile', action='store_true')

    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument('-e', '--entrypoint')
    type_group.add_argument('-c', '--command')
    type_group.add_argument('-x', '--execfile')

    parser.add_argument('-n', '--name')
    parser.add_argument('bundle_path')

    args = parser.parse_args()

    if args.force and os.path.exists(args.bundle_path):
        shutil.rmtree(args.bundle_path)

    build_one(
        bundle_path=args.bundle_path,
        name=args.name,

        compile=args.compile,
        profile=args.profile,

        entrypoint=args.entrypoint,
        command=args.command,
        execfile=args.execfile,
    )
