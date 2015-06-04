from distutils.command.build import build as orig_build
from distutils.cmd import Command
import os
import shutil

from setuptools.command.install import install as orig_install

from .build import build_app as _build_app


class build(Command):

    description = "\"build\" metatools's OS X applications."

    user_options = [
        ('build-dir=', 'd', "directory to \"build\" (copy) to"),
    ]

    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        if not self.build_dir:
            self.set_undefined_options('build', ('build_base', 'build_dir'))
            self.build_dir = os.path.join(self.build_dir, 'apps')

    def run(self):

        kwargs_list = getattr(self.distribution, 'metatools_apps', None)
        if not kwargs_list:
            return
        if isinstance(kwargs_list, dict):
            kwargs_list = [kwargs_list]

        for kwargs in kwargs_list:
            name = kwargs['name']
            bundle_path = kwargs.setdefault('bundle_path', os.path.join(self.build_dir, name + '.app'))

            if os.path.exists(bundle_path):
                shutil.rmtree(bundle_path)

            print name, kwargs['bundle_path']
            _build_app(**kwargs)




_build_commands = [
    ('build_metatools_apps', lambda self: True),
]

def _bootstrap_distutils():
    for cmd in _build_commands:
        if not any(x[0] == cmd[0] for x in orig_build.sub_commands):
            orig_build.sub_commands.append(cmd)


def verify_setup_kwarg(dist, attr, value):
    _bootstrap_distutils()
    return isinstance(value, (dict, list, tuple))

