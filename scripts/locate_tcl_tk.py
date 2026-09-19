#!/usr/bin/env python3
"""Locate the Tcl/Tk library files Nuitka's tk-inter plugin needs on Windows.

Python 3.14's official Windows installer ships Tcl/Tk 9 with its script
library packed into a zip appended directly to tcl90.dll/tcl9tk90.dll (under
DLLs\\) and mounted via Tcl's zipfs, instead of as loose files or a
standalone .zip. Nuitka's tk-inter plugin (as of 4.2.1) only looks for
unpacked directories or standalone "tcl*.zip"/"libtcl*.zip" files, so it
can't find this layout on its own - see
https://github.com/Nuitka/Nuitka/issues/3993. This resolves the real
physical file backing each zipfs mount so build.ps1 can hand Nuitka a real
path via --tcl-library-dir/--tk-library-dir.

Prints a JSON object {"tcl": <path>, "tk": <path>} to stdout. A path may
point at either a directory (script library already unpacked - no
workaround needed) or a file (to be copied to a .zip for Nuitka).
"""

from __future__ import annotations

import json
import tkinter


def _physical_path(tk: tkinter.Tcl, library_path: str) -> str:
    mounts = tk.splitlist(tk.eval("zipfs mount"))
    for mount_point, physical_file in zip(mounts[0::2], mounts[1::2]):
        if library_path.startswith(mount_point):
            return physical_file

    return library_path


def main() -> None:
    root = tkinter.Tk()
    root.withdraw()
    try:
        tcl_library = str(root.tk.eval("info library"))
        tk_library = str(root.tk.getvar("tk_library"))

        result = {
            "tcl": _physical_path(root.tk, tcl_library),
            "tk": _physical_path(root.tk, tk_library),
        }
    finally:
        root.destroy()

    print(json.dumps(result))


if __name__ == "__main__":
    main()
