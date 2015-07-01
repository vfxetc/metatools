from .utils import resolve_relative_name
from .reload import is_outdated, reload, autoreload
from .entry_points import load_entry_point

# for b/c
load_entrypoint = load_entry_point

# silence pyflakes
assert is_outdated and reload and autoreload and resolve_relative_name and load_entrypoint

