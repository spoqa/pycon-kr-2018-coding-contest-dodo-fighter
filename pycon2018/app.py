import collections
import datetime
import typing

from dateutil.parser import parse as parse_datetime
from settei import config_property, Configuration
from sqlalchemy.engine import create_engine, Engine
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import cached_property

from .orm import Session


class App(Configuration):
    database_url = config_property(
        'database.url', str
    )

    github_oauth_client_id = config_property(
        'github.oauth_client_id', str
    )

    github_oauth_client_secret = config_property(
        'github.oauth_client_secret', str
    )

    secret_key = config_property(
        'web.secret_key', str
    )

    game_round_time = config_property(
        'game.duration', int, default=30
    )

    game_round_count = config_property(
        'game.round_count', int, default=3
    )

    game_hit_point_min = config_property(
        'game.hit_point_min', int, default=12
    )

    game_hit_point_max = config_property(
        'game.hit_point_max', int, default=16
    )

    game_hit_point_guard_min = config_property(
        'game.hit_point_guard_min', int, default=4
    )

    game_hit_point_guard_max = config_property(
        'game.hit_point_guard_max', int, default=8
    )

    game_evaluator_path = config_property(
        'game.evaluator_path', str, default='script_runner'
    )

    game_p1_initial_position = config_property(
        'game.p1_initial_position', int, default=0
    )

    game_p2_initial_position = config_property(
        'game.p2_initial_position', int, default=3
    )

    sentry_dsn = config_property(
        'sentry.dsn', str, default=None
    )

    @property
    def game_hit_point_range(self) -> typing.Tuple[int]:
        return (self.game_hit_point_min, self.game_hit_point_max)

    @property
    def game_hit_point_guard_range(self) -> typing.Tuple[int]:
        return (self.game_hit_point_guard_min, self.game_hit_point_guard_max)

    @cached_property
    def database_engine(self) -> Engine:
        url = self.database_url
        db_options = dict(self.get('database', ()))
        db_options.pop('url', None)
        return create_engine(url, **db_options)

    def create_session(self, bind=None) -> Session:
        if bind is None:
            bind = self.database_engine
        return Session(bind=bind)

    @cached_property
    def web_config(self) -> collections.abc.Mapping:
        web_config = self.config.get('web', {})
        if not isinstance(web_config, collections.abc.Mapping):
            web_config = {}
        return ImmutableDict((k.upper(), v) for k, v in web_config.items())
