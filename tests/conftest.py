from __future__ import annotations

import sys

# Mirrors scripts/test.py's --ignore flags so a bare `pytest` invocation
# (e.g. an IDE's test runner, which doesn't go through that wrapper) skips
# the same platform-inappropriate directories CI does, instead of failing on
# tests that assert POSIX-only behaviour (chmod bits, socket permissions) on
# Windows or vice versa.
if sys.platform == "win32":
    collect_ignore_glob = ["platform/linux/*", "unit/ui/gui/*"]

else:
    collect_ignore_glob = ["platform/windows/*"]
