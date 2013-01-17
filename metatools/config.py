"""

- yml files

- metatools.config.get('key_base/3d/cam_cache/exporter', 'tab', 0)
    section, name, default

- metatools.config.Config('key_base/maya/cam_cache/exporter') as config:
    config.get('tab', 0)
    config['tab'] = 0

  Config.save()
  Config.revert()
  Config.delete()

python -m metatools.config <section> <name>
python -m metatools.config <section> <name> <value>
python -m metatools.config --unset <section> <name>
python -m metatools.config --unset <section>

"""

import os

import yaml


class Config(dict):

    def __init__(self, name):
        self.name = name
        if os.path.isabs(name):
            self.path = name
        else:
            self.path = os.path.expanduser('~/.%s.yml' % name)
        self.revert()

    def revert(self):
        if not os.path.exists(self.path):
            self.clear()
        else:
            saved = yaml.load(open(self.path).read())
            self.clear()
            self.update(saved)
        self.dirty = False

    def save(self, force=False):
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
