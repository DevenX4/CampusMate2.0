"""Errors raised by services. They describe WHAT went wrong in domain terms; the API layer
(app/api/errors.py) decides which HTTP status code that becomes. Services never import FastAPI."""


class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' not found")


class ConflictError(Exception):
    """The request is valid but conflicts with the current state (e.g. email already in use,
    or an admin trying to deactivate their own account)."""
