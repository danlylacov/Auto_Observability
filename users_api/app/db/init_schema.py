"""Create app_users table and bootstrap maintainer."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import engine
from app.models.user import User, UserRole
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_schema_and_bootstrap() -> None:
    settings = get_settings()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(128) NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(32) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
                )
                """
            )
        )

    with Session(engine) as db:
        has_maintainer = (
            db.query(User)
            .filter(User.role == UserRole.maintainer.value)
            .first()
        )
        if has_maintainer is None:
            u = settings.maintainer_username.strip()
            p = settings.maintainer_password
            if not u:
                logger.warning("MAINTAINER_USERNAME empty; skipping maintainer bootstrap")
                return
            existing = db.query(User).filter(User.username == u).first()
            if existing:
                if existing.role != UserRole.maintainer.value:
                    existing.role = UserRole.maintainer.value
                    existing.password_hash = pwd_context.hash(p)
                    existing.is_active = True
                    db.commit()
                    logger.info("Promoted existing user %s to maintainer", u)
                return
            user = User(
                username=u,
                password_hash=pwd_context.hash(p),
                role=UserRole.maintainer.value,
                is_active=True,
            )
            db.add(user)
            db.commit()
            logger.info("Created bootstrap maintainer user %s", u)
