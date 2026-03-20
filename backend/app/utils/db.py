# app/utils/db.py — Database connection pool and query helpers
# Uses SQLAlchemy Core (not ORM) for fine-grained SQL control

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from flask import current_app, g
import logging

logger = logging.getLogger(__name__)

# Module-level engine (shared across requests)
_engine = None


def init_db(app):
    """
    Called once at app startup to create the SQLAlchemy engine.
    """
    global _engine
    _engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        poolclass=QueuePool,
        pool_size=app.config["SQLALCHEMY_POOL_SIZE"],
        pool_timeout=app.config["SQLALCHEMY_POOL_TIMEOUT"],
        pool_recycle=app.config["SQLALCHEMY_POOL_RECYCLE"],
        echo=app.config["DEBUG"],   # Log SQL in dev mode
    )
    logger.info("Database engine initialised.")


def get_db():
    """
    Returns a database connection from the pool.
    Stored on Flask's request context (g) so one connection
    is reused per request and automatically closed after.
    """
    if "db" not in g:
        g.db = _engine.connect()
    return g.db


def close_db(e=None):
    """
    Closes the DB connection at the end of each request.
    Registered via app.teardown_appcontext in create_app.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def execute_query(sql: str, params: dict = None):
    """
    Executes a SELECT query and returns all rows as dicts.
    """
    conn = get_db()
    result = conn.execute(text(sql), params or {})
    return [dict(row._mapping) for row in result]


def execute_one(sql: str, params: dict = None):
    """
    Executes a SELECT query and returns the first row as a dict,
    or None if no rows found.
    """
    rows = execute_query(sql, params)
    return rows[0] if rows else None


def execute_write(sql: str, params: dict = None):
    """
    Executes an INSERT / UPDATE / DELETE.
    Returns the lastrowid for INSERT statements.
    Auto-commits the transaction.
    """
    conn = get_db()
    result = conn.execute(text(sql), params or {})
    conn.commit()
    return result.lastrowid


def call_procedure(proc_name: str, args: list):
    """
    Calls a MySQL stored procedure using raw PyMySQL connection.
    Used for sp_book_slot which uses OUT parameters.
    Returns the OUT parameter values.
    """
    conn = get_db()
    # Access underlying DBAPI connection for callproc support
    raw = conn.connection.cursor()
    raw.callproc(proc_name, args)
    conn.commit()
    # Fetch OUT param values by re-querying @_procname_N variables
    raw.execute(
        f"SELECT @_{proc_name}_3 as result"  # index of OUT param
    )
    row = raw.fetchone()
    raw.close()
    return row[0] if row else None