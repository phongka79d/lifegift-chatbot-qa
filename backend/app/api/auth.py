"""Authentication dependencies supporting anonymous and authenticated users."""

from typing import Optional
from fastapi import Header, HTTPException, status


async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> Optional[int]:
    """Extract authenticated user id from header if present, allowing anonymous access."""
    if x_user_id:
        try:
            return int(x_user_id)
        except ValueError:
            pass

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        # Mock bearer token decoding: "user_1", "user_2" or numeric string
        if token.startswith("user_"):
            try:
                return int(token.replace("user_", ""))
            except ValueError:
                pass
        try:
            return int(token)
        except ValueError:
            pass

    return None


async def get_required_current_user(
    user_id: Optional[int] = Header(None, alias="X-User-Id"),
    authorization: Optional[str] = Header(None),
) -> int:
    """Enforce authenticated user requirement."""
    uid = await get_optional_current_user(authorization=authorization, x_user_id=str(user_id) if user_id else None)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return uid
