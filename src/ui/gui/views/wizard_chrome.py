from __future__ import annotations

import tkinter as tk

# ────────────────────────────────────────────────────────────────| Chrome |──
#
# Shared header/button-row builders so the install wizard and the (simpler,
# single-window) uninstall flow present one consistent look instead of each
# re-declaring its own label/button styling.

TITLE_FONT = ("sans-serif", 12, "bold")
BODY_FONT = ("sans-serif", 10)


def build_header(parent: tk.Misc, title: str, subtitle: str = "") -> tk.Frame:
    """Build the wizard-style header banner shown atop every page/screen.

    Args:
        parent (tk.Misc): Widget to pack the header into.
        title (str): Bold headline text.
        subtitle (str): Optional smaller line shown below the title.

    Returns:
        tk.Frame: The packed header frame (already added to *parent*).
    """

    header = tk.Frame(parent, relief="groove", borderwidth=1)
    header.pack(fill="x")

    tk.Label(
        header,
        text=title,
        anchor="w",
        font=TITLE_FONT,
    ).pack(fill="x", padx=12, pady=(10, 0 if subtitle else 10))

    if subtitle:
        tk.Label(
            header,
            text=subtitle,
            anchor="w",
            font=BODY_FONT,
        ).pack(fill="x", padx=12, pady=(0, 10))

    return header


def build_button_row(parent: tk.Misc) -> tk.Frame:
    """Build the right-aligned button row shown at the bottom of every
    page/screen.

    Args:
        parent (tk.Misc): Widget to pack the button row into.

    Returns:
        tk.Frame: The packed, empty button row frame - callers pack their
            own tk.Button children into it, right-aligned.
    """

    row = tk.Frame(parent)
    row.pack(fill="x", padx=10, pady=(4, 10), side="bottom")

    return row
