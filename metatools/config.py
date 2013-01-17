"""Tools for easy persistance of configuration and user preferences for tools.

Configurations are split into sections and keys; sections are conceptually for
each tool (or other grouping of settings), and keys are for individual settings
within that tool/section. In the current implementation, individual sections
are saved within YAML files as a mapping.

Basic usage::
    
    # Creating the config object; give it a unique name. Slashes will be
    # used directly to specify sub-directories.
    config = metatools.config.Config('your_company/' + __name__)

    # Use a value within the config; treat it like a dict.
    dialog = setup_gui(width=config.get('width', 800))

    # Save the values later.
    config['width'] = dialog.width()
    config.save() # Only if there were changes to the values.

Quick use::

    width = metatools.config.get('your_company/' + __name__, 'width') 
    metatools.config.set('your_company/' + __name__, 'width', width)


"""

import os

import yaml


class Config(dict):
    """Mapping which persists to disk via YAML serialization.

    Use like a dictionary.

    """

    def __init__(self, name):
        self.name = name
        if os.path.isabs(name):
            self.path = name
        else:
            self.path = os.path.expanduser('~/.%s.yml' % name)
        self.revert()

    def revert(self):
        """Revert to saved state."""
        if not os.path.exists(self.path):
            self.clear()
        else:
            saved = yaml.load(open(self.path).read())
            self.clear()
            self.update(saved)
        self.dirty = False

    def save(self, force=False):
        """Persist the current contents.

        :param bool force: Always write, even if there were no changes.

        """

        if not force and not self.dirty:
            return
        if self:
            encoded = yaml.dump(dict(self),
                indent=4,
                default_flow_style=False,
            )
            directory = os.path.dirname(self.path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            with open(self.path, 'wb') as fh:
                fh.write(encoded)
        elif os.path.exists(self.path):
            os.unlink(self.path)

    def delete(self):
        """Clear and delete; same as clear() and save()."""
        self.clear()
        if os.path.exists(self.path):
            os.unlink(self.path)

    def __setitem__(self, key, value):
        super(Config, self).__setitem__(key, value)
        self.dirty = True

    def update(self, *args, **kwargs):
        super(Config, self).update(*args, **kwargs)
        self.dirty = True

    def __delitem__(self, key):
        super(Config, self).__delitem__(key)
        self.dirty = True

    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        if not type_:
            self.save()


def get(section, name, *args):
    config = Config(section)
    try:
        return config[name]
    except KeyError:
        if args:
            return args[0]
        else:
            raise


def set(section, name, value):
    config = Config(section)
    config[name] = value
    config.save()


def main():

    import ast
    from optparse import OptionParser

    optparser = OptionParser('%prog [options] section name [value]')
    opts, args = optparser.parse_args()

    # Basic get.
    if len(args) == 2:
        print get(*args)

    # Basic set.
    elif len(args) == 3:
        section, name, raw_value = args
        try:
            value = ast.literal_eval(raw_value)
        except SyntaxError:
            value = raw_value
        set(section, name, value)

    else:
        optparser.print_usage()
        exit(1)


if __name__ == '__main__':
    main()
