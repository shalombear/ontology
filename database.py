from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import event

projects = Path(__file__).resolve().parent.parent
db_path = projects / 'data' / 'db' / 'wikipull.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

engine = sa.create_engine(f"sqlite:///{db_path.as_posix()}")

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

metadata = sa.MetaData()

articles = sa.Table(
    'articles', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('path', sa.String, unique=True, nullable=False),
    sa.Column('scanned', sa.Boolean, nullable=False, server_default='0')
)

edges = sa.Table(
    'edges', metadata,
    sa.Column('parent_id', sa.Integer, sa.ForeignKey('articles.id'), nullable=False),
    sa.Column('child_id', sa.Integer, sa.ForeignKey('articles.id'), nullable=False),
    sa.PrimaryKeyConstraint('parent_id', 'child_id')
)

seeds = sa.Table(
    'seeds', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('article_id', sa.Integer, sa.ForeignKey('articles.id'), nullable=False, unique=True),
    sa.Column('max_depth', sa.Integer, nullable=False)
)

seed_nodes = sa.Table(
    'seed_nodes', metadata,
    sa.Column('seed_id', sa.Integer, sa.ForeignKey('seeds.id'), nullable=False),
    sa.Column('article_id', sa.Integer, sa.ForeignKey('articles.id'), nullable=False),
    sa.Column('depth', sa.Integer, nullable=False),
    sa.Column('expanded', sa.Boolean, nullable=False, server_default='0'),
    sa.PrimaryKeyConstraint('seed_id', 'article_id')
)

if __name__ == '__main__':
    metadata.create_all(engine)