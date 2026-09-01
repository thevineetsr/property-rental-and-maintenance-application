from typing import List
from fastapi import Depends, HTTPException, status
from backend.app.dependencies.auth import get_current_user
from backend.app.models.user import User, UserRole


def require_role(*allowed_roles: UserRole):
    """Enforce role-based access control on the FastAPI server."""
    allowed_values = [r.value if isinstance(r, UserRole) else r for r in allowed_roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of the following roles: {', '.join(allowed_values)}"
            )
        return current_user

    return role_checker


# Specific role dependencies for convenience
require_manager = require_role(UserRole.PROPERTY_MANAGER)
require_contractor = require_role(UserRole.MAINTENANCE_CONTRACTOR)
require_authenticated = get_current_user
