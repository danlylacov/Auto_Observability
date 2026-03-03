from app.db.postgres.database import Base, engine
from app.models.postgres import Container, PrometheusConfig  # noqa: F401
from app.models.postgres.host import Host  # noqa: F401


def init_db() -> None:
    """
    Создание всех таблиц
    """
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
