from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from flask import current_app, g
import logging
import datetime

logger = logging.getLogger(__name__)
_engine = None

def init_db(app):
    global _engine
    _engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        poolclass=QueuePool,
        pool_size=app.config["SQLALCHEMY_POOL_SIZE"],
        pool_timeout=app.config["SQLALCHEMY_POOL_TIMEOUT"],
        pool_recycle=app.config["SQLALCHEMY_POOL_RECYCLE"],
        echo=app.config["DEBUG"],
    )
    logger.info("Database engine initialised.")

def get_db():
    if "db" not in g:
        g.db = _engine.connect()
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def _serialize(v):
    if isinstance(v, datetime.timedelta):
        total = int(v.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    elif isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return v

def execute_query(sql, params=None):
    conn = get_db()
    result = conn.execute(text(sql), params or {})
    rows = []
    for row in result:
        d = {k: _serialize(v) for k, v in dict(row._mapping).items()}
        rows.append(d)
    return rows

def execute_one(sql, params=None):
    rows = execute_query(sql, params)
    return rows[0] if rows else None

def execute_write(sql, params=None):
    conn = get_db()
    result = conn.execute(text(sql), params or {})
    conn.commit()
    return result.lastrowid
