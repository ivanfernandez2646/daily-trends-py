class UnauthorizedError(Exception):
    """The caller is not authenticated: no credentials, or credentials that are not valid."""
