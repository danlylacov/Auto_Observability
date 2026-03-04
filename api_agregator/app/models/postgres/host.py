import uuid

from app.db.postgres.database import Base
from sqlalchemy import Column, String, Integer


class Host(Base):
    __tablename__ = "hosts"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255))
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)