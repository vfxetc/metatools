from distutils.command.build import build as orig_build
from distutils.cmd import Command
import os

from setuptools.command.install import install as orig_install

from .build import build as _build


class build(Command):

    description = "build metatools's scripts."

    user_options = [
        ('build-dir=', 'd', "directory to \"build\" (copy) to"),
        # See distutils.command.build_script for more good ideas!
    ]

    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        # Pull in options from the "build" command.
        self.set_undefined_options('build',
            ('build_scripts', 'build_dir'), 
        )

    def run(self):
        path = (
            getattr(self.distribution, 'metatools_scripts', None) or
            getattr(self.distribution, 'metatools_entrypoints', None)
        )
        if path:
            if not os.path.exists(self.build_dir):
                os.makedirs(self.build_dir)
            _build(path, self.build_dir)


class install(Command):

    description = "install metatools's scripts."

    user_options = [
        ('install-dir=', 'd', "directory to install scripts to"),
        ('build-dir=','b', "build directory (where to install from)"),
        ('skip-build', None, "skip the build steps"),
        # See distutils.command.build_script for more good ideas!
    ]

    def initialize_options(self):
        self.build_dir = None
        self.install_dir = None
        self.skip_build = None

    def finalize_options(self):
        self.set_undefined_options('build',
            ('build_scripts', 'build_dir'),
        )
        self.set_undefined_options('install',
            ('install_scripts', 'install_dir'),
            ('skip_build', 'skip_build'),
        )

    def run(self):
        if not self.skip_build:
            self.run_command('build_metatools_scripts')
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

    def get_inputs(self):
        return [] # TODO: Does this being wrong mess with anything?

    def get_outputs(self):
        return self.outfiles or []





_build_commands = [
    ('build_metatools_entrypoints', lambda self: True),
]
_install_commands = [
    ('install_metatools_entrypoints', lambda self: True),
]

def _bootstrap_distutils():
    for cmd in _build_commands:
        if not any(x[0] == cmd[0] for x in orig_build.sub_commands):
            orig_build.sub_commands.append(cmd)
    for cmd in _install_commands:
        if not any(x[0] == cmd[0] for x in orig_install.sub_commands):
            orig_install.sub_commands.append(cmd)


def verify_setup_kwarg(dist, attr, value):
    _bootstrap_distutils()
    return os.path.exists(value)

