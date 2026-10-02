"""Flask extensions, created here unbound and attached to an app in `create_app`.

Living in their own module lets models and views import `db` without importing the app,
which would be a circular import.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Explicit constraint names, so migrations can refer to (and later drop) constraints by name
# instead of whatever the database happened to generate.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
