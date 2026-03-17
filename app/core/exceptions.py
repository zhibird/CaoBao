class EntityConflictError(Exception):
    """Raised when creating an entity that already exists."""


class EntityNotFoundError(Exception):
    """Raised when the requested entity does not exist."""


class DomainValidationError(Exception):
    """Raised when an entity exists but violates a business rule."""
