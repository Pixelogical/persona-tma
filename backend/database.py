from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import BASE_DIR, settings

_url = settings.database_url

# Resolve relative sqlite paths against the backend directory so the app
# can be started from anywhere.
if _url.startswith("sqlite:///") and not _url.startswith("sqlite:////"):
    rel = _url.replace("sqlite:///", "", 1)
    if rel != ":memory:":
        path = (BASE_DIR / rel).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        _url = f"sqlite:///{path}"

engine = create_engine(
    _url,
    connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {},
)

if _url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _drop_legacy_unique() -> None:
    """One-time migration: older schema had UNIQUE(songs.file_unique_id) which
    silently swallowed every re-sent mp3. SQLite needs a table rebuild."""
    from sqlalchemy import inspect
    from sqlalchemy import text

    from models import Song

    insp = inspect(engine)
    if "songs" not in insp.get_table_names():
        return
    # UNIQUE constraints live in sqlite_autoindex_* which the inspector hides,
    # so look at the raw PRAGMA output.
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA index_list(songs)").fetchall()
    has_unique = any(int(r[2]) == 1 for r in rows)
    if not has_unique:
        return

    cols = [c["name"] for c in insp.get_columns("songs")]
    keep = [c.key for c in Song.__table__.columns if c.key in cols]
    collist = ", ".join(keep)

    conn = engine.connect()
    try:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("PRAGMA legacy_alter_table=ON"))
        conn.execute(text("ALTER TABLE songs RENAME TO songs_legacy"))
        conn.commit()
    finally:
        conn.close()

    Base.metadata.create_all(bind=engine)  # fresh songs table + plain index

    with engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT INTO songs ({collist}) "
                f"SELECT {collist} FROM songs_legacy"
            )
        )
        conn.execute(text("DROP TABLE songs_legacy"))
    print("migrated: removed UNIQUE constraint on songs.file_unique_id")


def init_db() -> None:
    from models import Base as _  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    _drop_legacy_unique()
