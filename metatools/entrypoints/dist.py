from distutils.command.build import build as orig_build
from distutils.cmd import Command
import os

from setuptools.command.install import install as orig_install

from .build import build as _build


class build(Command):

    description = "\"build\" metatools's entrypoints scripts."

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
        path = getattr(self.distribution, 'metatools_entrypoints', None)
        if path:
            if not os.path.exists(self.build_dir):
                os.makedirs(self.build_dir)
            _build(path, self.build_dir)





sub_commands = [
    ('build_metatools_entrypoints', lambda self: True),
]

def _bootstrap_distutils():
    for sub_command in sub_commands:
        if not any(x[0] == sub_command[0] for x in orig_build.sub_commands):
            orig_build.sub_commands.append(sub_command)

def verify_setup_kwarg(dist, attr, value):
    _bootstrap_distutils()
    return os.path.exists(value)

