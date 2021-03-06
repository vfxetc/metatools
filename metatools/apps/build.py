from distutils import sysconfig
from distutils.ccompiler import new_compiler
from subprocess import call, check_call, check_output
import argparse
import datetime
import glob
import os
import re
import shutil
import sys
import tempfile
import plistlib

import yaml


from metatools.utils import dedent



def parse_envvar(x):
    x = x.split('=', 1)
    if len(x) != 2:
        raise ValueError('envvar missing equals')
    return x[0].strip(), x[1].strip()


def get_template_path(name):
    return os.path.abspath(os.path.join(__file__, '..', 'templates', name))


def read_template(name):
    return open(get_template_path(name), 'rb').read()


def render_template(name_, **kw):
    content = read_template(name_)
    return re.sub(r'METATOOLS_([A-Z_]+)', lambda m: kw.get(m.group(1), ''), content)


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

    c_source_path = get_template_path('bootstrap.c')
    build_dir = tempfile.mkdtemp(prefix='metatools_app.%s.' % os.path.basename(target))
    objs = cc.compile([c_source_path], build_dir, extra_preargs=c_flags,
        macros=[('METATOOLS_BOOTSTRAP_SOURCE', '"%s"' % source.encode('string-escape'))],
    )
    cc.link(cc.EXECUTABLE, objs, target, extra_preargs=ld_flags)

    shutil.rmtree(build_dir)


def register_app(bundle_path, identifier=None):

    lsregister = '/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister'
    dump = check_output([lsregister, '-dump'])

    if identifier:
        for chunk in re.split(r'-{10,}', dump):
            if not re.search(r'identifier:\s+%s' % identifier, chunk):
                continue
            m = re.search(r'path:\s+([^\n]+)', chunk)
            old_path = m.group(1)
            if old_path != bundle_path:
                print 'lsregister: unregistering', old_path
                check_call([lsregister, '-u', old_path])

    call([lsregister, '-v', '-f', bundle_path])


def copy_icon(bundle_path, icon):

    resources = os.path.join(bundle_path, 'Contents', 'Resources')
    if not os.path.exists(resources):
        os.makedirs(resources)

    name, ext = os.path.splitext(os.path.basename(icon))
    
    # Get a unique path.
    counter = 0
    path = os.path.join(resources, name + ext)
    while os.path.exists(path):
        counter += 1
        path = os.path.join(resources, '%s_%d%s' % (name, counter, ext))
    
    shutil.copy(icon, path)

    return os.path.basename(path)


def build_app(

    target_type,
    target,
    bundle_path,

    name=None,
    icon=None,
    version='1.0.0',
    identifier=None,

    source_profile=True,
    use_compiled_bootstrap=False,

    url_schemes=(),
    file_types=(),
    document_extensions=(),
    argv_emulation=False,
    on_open_url=None,
    on_open_document=None,

    python_path=(),
    envvars=(),

    plist_defaults=None,
    register=True,

):

    if not bundle_path.endswith('.app'):
        raise ValueError('bundle_path must end in .app')

    target_type = target_type or 'entrypoint'
    if target_type not in ('entrypoint', 'exec'):
        raise ValueError('unknown target_type %r' % target_type)

    if target_type == 'entrypoint':
        parts = target.split(':')
        if len(parts) > 2:
            raise ValueError('entrypoint must be "package.module" or "package.module:function"')

    elif target_type == 'exec' and use_compiled_bootstrap:
        raise ValueError('cannot compile bootstrap for external target')

    is_exec = target_type == 'exec'

    name = name or os.path.splitext(os.path.basename(bundle_path))[0]
    safe_name = re.sub(r'\W+', '_', name)
    identifier = identifier or 'com.keypics.%s' % safe_name

    # Make sure we have an empty bundle.
    if os.path.exists(bundle_path) and os.listdir(bundle_path):
        raise ValueError('bundle_path exists: %s' % bundle_path)
    os.makedirs(os.path.join(bundle_path, 'Contents', 'MacOS'))
    
    exes = filter(None, [
        ('profile', {'name': 'bootstrap_%s.sh' % safe_name}) if source_profile or is_exec else None,
        ('compile', {'name': 'bootstrap_%s'    % safe_name}) if use_compiled_bootstrap else None,
        ('primary', {'name': 'bootstrap_%s.py' % safe_name}) if not is_exec else None,
    ])
    exes[0][1]['name'] = safe_name
    for i, (type_, config) in enumerate(exes):
        config['next'] = exes[i + 1][0] if i + 1 < len(exes) else None
    exes = dict(exes)

    absolute_self = os.path.abspath(__file__)
    build_time = datetime.datetime.now()

    # Build the plist
    plist = (plist_defaults or {}).copy()
    plist.setdefault('CFBundleDisplayName', name)
    plist.setdefault('CFBundleIdentifier', identifier)
    plist.setdefault('CFBundleVersion', version)
    plist.setdefault('CFBundleExecutable', safe_name)

    # plist['CFBundleIconFile'] = ''
    plist.setdefault('CFBundleGetInfoString', 'Created by metatools')
    plist.setdefault('CFBundlePackageType', 'APPL')
    plist.setdefault('CFBundleSignature', '????')
    plist.setdefault('NSPrincipalClass', 'NSApplication')

    # This one MUST be set, even though Apple says it is not required. If it is
    # not set, and we use the compiled bootstrapper to that it takes effect, 
    # AND we use Qt, Qt will crash when trying to render the menu bar.
    plist.setdefault('CFBundleName', name)

    if icon:
        plist['CFBundleIconFile'] = copy_icon(bundle_path, icon)

    if url_schemes:
        plist.setdefault('CFBundleURLTypes', []).extend({
            'CFBundleURLName': '%s.%s' % (identifier, url_scheme),
            'CFBundleURLSchemes': [url_scheme],
        } for url_scheme in url_schemes)

    if file_types:
        file_type_plist = plist.setdefault('CFBundleDocumentTypes', [])
        for i, spec in enumerate(file_types):
            file_type = {
                'CFBundleTypeName': '%s.file%s' % (identifier, i),
                'CFBundleTypeExtensions': spec['extensions'],
            }
            if spec.get('icon'):
                file_type['CFBundleTypeIconFile'] = copy_icon(bundle_path, spec.get('icon'))
            if spec.get('rank'):
                file_type['LSHandlerRank'] = spec['rank']
            file_type_plist.append(file_type)

    plistlib.writePlist(plist, os.path.join(bundle_path, 'Contents', 'Info.plist'))

    
    # Build the profile bootstrapper.
    if source_profile or is_exec:
        contents = render_template('bootstrap.sh',
            TARGET=target,
            TARGET_TYPE=target_type,
            ENVVARS='\n'.join('export %s="%s"' % x for x in envvars),
            NEXT=exes.get(exes['profile']['next'], {}).get('name') or '',
            SELF=absolute_self,
            SOURCE_PROFILE=str(int(bool(source_profile))),
            TIME=str(build_time),
        )
        target_path = os.path.join(bundle_path, 'Contents', 'MacOS', exes['profile']['name'])
        with open(target_path, 'w') as fh:
            fh.write(contents)
        check_call(['chmod', 'a+x', target_path])

    # Build the compile bootstrapper.
    if use_compiled_bootstrap:
        target_path = os.path.join(bundle_path, 'Contents', 'MacOS', exes['compile']['name'])
        compile_bootstrap(target_path, dedent('''
            import os
            import sys
            __file__ = os.path.abspath(os.path.join(sys.argv[0], '..', %r))
            execfile(__file__)
        ''' % (exes['primary']['name'], ))) # Should use "next"?

    if argv_emulation or on_open_url or on_open_document:
        shutil.copy(
            get_template_path('bootstrap_apple_events.py'),
            os.path.join(bundle_path, 'Contents', 'MacOS', 'bootstrap_apple_events.py')
        )

    if not is_exec:
        # Build the Python bootstrapper.
        contents = render_template('bootstrap.py',
            ARGV_EMULATION=repr(argv_emulation),
            TARGET=repr(target),
            TARGET_TYPE=repr(target_type),
            ENVVARS='()' if source_profile else repr(envvars), # This will have already been handled.
            ON_OPEN_DOCUMENT=repr(on_open_document),
            ON_OPEN_URL=repr(on_open_url),
            PATH=repr(python_path),
            SELF=absolute_self,
            TIME=str(build_time),
        )
        target_path = os.path.join(bundle_path, 'Contents', 'MacOS', exes['primary']['name'])
        with open(target_path, 'w') as fh:
            fh.write(contents)
        if not use_compiled_bootstrap:
            check_call(['chmod', 'a+x', target_path])

    if register:
        register_app(bundle_path, identifier)


def _parse_file_type(input_):
    """
        Examples:
            'glpt;icon=/path/to/icon'
            'abc,dpx;rank=Alternate'
    """

    m = re.match(r'^(.*?)(?:[;:&](.*))?$', input_)
    extensions, kwarg_string = m.groups()

    parsed = dict(chunk.split('=', 1) for chunk in kwarg_string.split(';'))
    parsed['extensions'] = [ext.strip().strip('.') for ext in extensions.split(',')]
    return parsed


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--force', action='store_true')

    parser.add_argument('-n', '--name')
    parser.add_argument('-i', '--icon')

    parser.add_argument('--compile-bootstrap', action='store_true', help='use compiled bootstrapper')
    parser.add_argument('--source-profile', action='store_true', help='source bash profile')

    parser.add_argument('-u', '--url-scheme', action='append')
    parser.add_argument('--file-type', action='append', type=_parse_file_type)

    parser.add_argument('--argv-emulation', action='store_true', help='source bash profile')
    parser.add_argument('--on-open-url', help='BROKEN')
    parser.add_argument('--on-open-document', help='BROKEN')

    parser.add_argument('--python-path', action='append')
    parser.add_argument('--envvar', action='append', type=parse_envvar)

    parser.add_argument('-t', '--type', choices=['entrypoint', 'python', 'shell', 'exec', 'execfile'], default='entrypoint')

    parser.add_argument('target')
    parser.add_argument('bundle_path')

    args = parser.parse_args()

    if args.force and os.path.exists(args.bundle_path):
        shutil.rmtree(args.bundle_path)

    build_app(

        target=args.target,
        target_type=args.type,

        bundle_path=args.bundle_path,

        name=args.name,
        icon=args.icon,
        
        argv_emulation=args.argv_emulation,
        on_open_url=args.on_open_url,
        on_open_document=args.on_open_document,

        use_compiled_bootstrap=args.compile_bootstrap,
        source_profile=args.source_profile,

        python_path=args.python_path or (),
        envvars=args.envvar or (),

        url_schemes=args.url_scheme or (),
        file_types=args.file_type or (),

    )


if __name__ == '__main__':
    main()

