from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ASSIGNABLE_ROLES = {UserRole.admin.value, UserRole.dev.value, UserRole.user.value}


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    role: str = Field(description="admin, dev, or user")


class UserPatch(BaseModel):
    role: str | None = None
    password: str | None = Field(None, min_length=1, max_length=256)
    is_active: bool | None = None


def require_maintainer(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.maintainer.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Maintainer only")
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    _: Annotated[User, Depends(require_maintainer)],
    db: Session = Depends(get_db),
):
    rows = db.query(User).order_by(User.id).all()
    return rows


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    _: Annotated[User, Depends(require_maintainer)],
    db: Session = Depends(get_db),
):
    if body.role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}",
        )
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    u = User(
        username=body.username.strip(),
        password_hash=pwd_context.hash(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.patch("/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    body: UserPatch,
    maint: Annotated[User, Depends(require_maintainer)],
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.role == UserRole.maintainer.value and u.id != maint.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another maintainer",
        )
    if body.role is not None:
        if u.role == UserRole.maintainer.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change maintainer role via API",
            )
        if body.role not in ASSIGNABLE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}",
            )
        u.role = body.role
    if body.password is not None:
        u.password_hash = pwd_context.hash(body.password)
    if body.is_active is not None:
        if u.id == maint.id and not body.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself",
            )
        u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    return u
