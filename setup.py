from setuptools import setup, find_packages

setup(
    name='metatools',
    version='0.1.0b',
    description='Python tools for Python tools.',
    url='http://github.com/westernx/metatools',
    
    # Stubs of old modules.
    py_modules=['entrypoints', 'autoreload'],

    packages=find_packages(exclude=['build*', 'tests*']),
    
    author='Mike Boers',
    author_email='metatools@mikeboers.com',
    license='BSD-3',
    
    entry_points={
        'distutils.setup_keywords': [
            'metatools_entrypoints = metatools.entrypoints.dist:verify_setup_kwarg',
        ],
        'distutils.commands': [
            'build_metatools_entrypoints = metatools.entrypoints.dist:build',
            'install_metatools_entrypoints = metatools.entrypoints.dist:install',
        ],
    },

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
)