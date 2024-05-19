# vim: set fileencoding=utf-8
"""
Domika integration.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid


class DomikaBaseError(Exception):
    """Base error class."""


class AppSessionIdNotFoundError(DomikaBaseError):
    """No app session id found."""

    def __init__(self, app_session_id: uuid.UUID):
        super().__init__(f'App session id "{app_session_id}" not found.')
        self.app_session_id = app_session_id


class PushSessionIdNotFoundError(DomikaBaseError):
    """Push session id found on the integration."""

    def __init__(self, app_session_id: uuid.UUID):
        super().__init__(f'Push session id is missing for app session id "{app_session_id}".')
        self.app_session_id = app_session_id
