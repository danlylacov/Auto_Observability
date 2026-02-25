from app.db.postgres.database import Base, engine
from app.models.postgres import Container, PrometheusConfig


def init_db() -> None:
    """
    Создание всех таблиц
    """
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
