import os.path
import pkgutil
import typing

from alembic.command import downgrade, stamp
from alembic.config import Config
from alembic.environment import EnvironmentContext
from alembic.script import Script, ScriptDirectory
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import literal_column

__all__ = ('Base', 'Session', 'downgrade_database', 'get_alembic_config',
           'get_database_revision', 'import_all_modules',
           'initialize_database', 'upgrade_database')


Base = declarative_base()
Session = sessionmaker()


def make_repr(self) -> str:
    cls = type(self)
    mod = cls.__module__
    name = ('' if mod == '__main__ ' else mod + '.') + cls.__qualname__
    try:
        columns = type(self).__repr_columns__
    except AttributeError:
        columns = cls.__mapper__.primary_key
    names = (column if isinstance(column, str) else column.name
             for column in columns)
    pairs = ((name, getattr(self, name))
             for name in names
             if hasattr(self, name))
    args = ' '.join(k + '=' + repr(v) for k, v in pairs)
    return '<{0} {1}>'.format(name, args)


Base.__repr__ = make_repr


def get_alembic_config(engine: typing.Union[Engine, str]) -> Config:
    if isinstance(engine, Engine):
        url = str(engine.url)
    elif isinstance(engine, str):
        url = str(engine)
    else:
        raise TypeError('engine must be a string or an instance of sqlalchemy.'
                        'engine.Engine, not ' + repr(engine))
    cfg = Config()
    cfg.set_main_option('script_location', 'pycon2018:migrations')
    cfg.set_main_option('sqlalchemy.url', url)
    cfg.set_main_option('url', url)
    return cfg


def initialize_database(engine: Engine):
    import_all_modules()
    Base.metadata.create_all(engine, checkfirst=False)
    alembic_cfg = get_alembic_config(engine)
    stamp(alembic_cfg, 'head')


def get_database_revision(engine: Engine) -> typing.Optional[Script]:
    config = get_alembic_config(engine)
    script = ScriptDirectory.from_config(config)
    result = [None]

    def get_revision(rev, context):
        result[0] = rev and script.get_revision(rev)
        return []
    with EnvironmentContext(config, script, fn=get_revision, as_sql=False,
                            destination_rev=None, tag=None):
        script.run_env()
    return None if result[0] == () else result[0]


def upgrade_database(engine: Engine, revision: str='head'):
    config = get_alembic_config(engine)
    script = ScriptDirectory.from_config(config)

    def upgrade(rev, context):
        def update_current_rev(old, new):
            if old == new:
                return
            if new is None:
                context.impl._exec(context._version.delete())
            elif old is None:
                context.impl._exec(
                    context._version.insert().values(
                        version_num=literal_column("'%s'" % new)
                    )
                )
            else:
                context.impl._exec(
                    context._version.update().values(
                        version_num=literal_column("'%s'" % new)
                    )
                )

        if not rev and revision == 'head':
            import_all_modules()
            Base.metadata.create_all(engine)
            dest = script.get_revision(revision)
            update_current_rev(None, dest and dest.revision)
            return []
        return script._upgrade_revs(revision, rev)
    with EnvironmentContext(config, script, fn=upgrade, as_sql=False,
                            destination_rev=revision, tag=None):
        script.run_env()


def downgrade_database(engine: Engine, revision: str):
    config = get_alembic_config(engine)
    downgrade(config, revision)


def import_all_modules():
    current_dir = os.path.join(os.path.dirname(__file__), '..')
    modules = frozenset(mod
                        for _, mod, __ in pkgutil.walk_packages(current_dir)
                        if mod.startswith('pycon2018.'))
    for mod in modules:
        __import__(mod)
    return modules
