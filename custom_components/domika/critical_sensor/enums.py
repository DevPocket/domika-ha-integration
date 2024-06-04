# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import enum


class CriticalityLevel(enum.Flag):
    """Critical sensor criticality level."""

    CRITICAL = enum.auto()
    WARNING = enum.auto()
    ANY = CRITICAL | WARNING

    def to_string(self) -> str:
        """
        Convert flag to string.

        Returns:
            string flags representation.
        """
        return '|'.join(flag.name.lower() for flag in self)
