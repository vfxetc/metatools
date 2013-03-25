.. _apps:

App Bundles for OS X
====================

Overview
--------

Since our users are often more amenable to the standard GUI interface, we need a way to quickly provide double-clickable apps so that they do not need to use the terminal. While something like Py2App_ would do the trick, these are unnesesarily heavy-weight for our needs.

.. _Py2App: http://pythonhosted.org/py2app/

Instead, this package directly constructs ``.app`` packages, with the bare minimum required for OS X to recognize them as applications and know how to launch them; they are essentially stubs for either existing commands or Python functions, but with icons.

Each app is specified by its own YAML_ file. The following keys are accepted:

.. _YAML: http://www.yaml.org/

``name``
    The name of the app. Defaults to the base name of the config file. E.g. A YAML file named ``toolbox.yml`` will default to generating an app named ``toolbox``.
    
``icon``
    The name of an icon in ``$KS_TOOLS/key_base/2d/icons``, or an absolute path. Defaults to the value of ``name``.
    
``entrypoint``
    Either ``"package.module"`` or ``"package.module:function"`` specifying which module to import/run

``command``
    A command to run as if from a shell. Defaults to the value of ``name`` if ``entrypoint`` is also not specified. Cannot be specified along with ``entrypoint``.


As you can see, given the defaults above, it is possible to fully describe an app in this manner with a completely empty YAML file!


Building Apps
-------------

Apps are build by running the main method of the ``metatools.apps`` module. It takes any number of YAML files as arguments, with the last argument being the directory to save the apps into. For example::

    python -m metatools.apps *.yml ./

will build all the YAML files in the current directory into apps also in the current directory.
