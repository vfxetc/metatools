from .reload import is_outdated, reload, autoreload

# Silence pyflakes
assert is_outdated and reload and autoreload
