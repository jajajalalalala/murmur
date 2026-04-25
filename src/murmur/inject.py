"""Place transcribed text in front of the user.

v0.2 keeps it simple: copy to the clipboard. v0.3 will add an
auto-paste step that simulates Cmd/Ctrl-V at the focused window.
"""
from __future__ import annotations

import pyperclip


def to_clipboard(text: str) -> bool:
    if not text:
        return False
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException:
        return False
