from setuptools import setup, find_packages

setup(
    name='metatools',
    version='0.2.0a0',
    description='Python tools for Python tools.',
    url='http://github.com/westernx/metatools',
        
    author='Mike Boers',
    author_email='metatools@mikeboers.com',
    license='BSD-3',
    
    # Stubs of old modules.
    py_modules=['entrypoints', 'autoreload'],

    packages=find_packages(exclude=['build*', 'tests*']),

    include_package_data=True,
    
    entry_points={
        'distutils.setup_keywords': [
            'metatools_entrypoints = metatools.scripts.dist:verify_setup_kwarg', # Deprecated.
            'metatools_scripts = metatools.scripts.dist:verify_setup_kwarg',
            'metatools_apps = metatools.apps.dist:verify_setup_kwarg',
        ],
        'distutils.commands': [
            'build_metatools_scripts = metatools.scripts.dist:build',
            'install_metatools_scripts = metatools.scripts.dist:install',
            'build_metatools_apps = metatools.apps.dist:build',
            # 'install_metatools_apps = metatools.apps.dist:install',
        ],
        'console_scripts': '''
            metatools_scripts = metatools.scripts.build:main
            metatools_apps    = metatools.apps.build:main
        ''',
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