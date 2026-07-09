from sqlalchemy import inspect, text

from app.db.database import engine
from app.db.models import Base


def _migrate_notification_subscriptions() -> None:
    inspector = inspect(engine)
    if "notification_subscriptions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notification_subscriptions")}

    with engine.begin() as conn:
        if "chart_interval_seconds" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE notification_subscriptions "
                    "ADD COLUMN chart_interval_seconds INTEGER NOT NULL DEFAULT 600"
                )
            )
        if "last_chart_sent_at" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE notification_subscriptions "
                    "ADD COLUMN last_chart_sent_at BIGINT"
                )
            )


def init():
    Base.metadata.create_all(bind=engine)
    _migrate_notification_subscriptions()


if __name__ == "__main__":
    init()
