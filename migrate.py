#!/usr/bin/env python3
import logging.config
import pathlib

from alembic.config import CommandLine

from pycon2018.app import App
from pycon2018.orm import get_alembic_config, import_all_modules


ALEMBIC_LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'NOTSET',
            'class': 'logging.StreamHandler',
            'formatter': 'generic'
        }
    },
    'formatters': {
        'generic': {
            'format': '%(levelname)-5.5s [%(name)s] %(message)s',
            'datefmt': '%H:%M:%S'
        }
    },
    'root': {
        'level': 'WARN',
        'handlers': ['console']
    },
    'loggers': {
        'alembic': {
            'level': 'INFO',
            'handlers': []
        },
        'sqlalchemy.engine': {
            'level': 'WARN',
            'handlers': []
        }
    }
}


class AlembicCli(CommandLine):
    """Customized :prog:`alembic` command for the project."""

    def _generate_args(self, prog):
        super()._generate_args(prog)
        # Make -c/--config option required
        config_action = next(action
                             for action in self.parser._actions
                             if '--config' in action.option_strings)
        config_action.required = True
        config_action.default = None

    def main(self, argv=None):
        options = self.parser.parse_args(argv)
        if not hasattr(options, 'cmd'):
            # see http://bugs.python.org/issue9253, argparse
            # behavior changed incompatibly in py3.3
            self.parser.error('too few arguments')
        config_path = pathlib.Path(options.config)
        try:
            app = App.from_path(config_path)
        except FileNotFoundError as e:
            self.parser.error(str(e))
        cfg = get_alembic_config(app.database_url)
        import_all_modules()
        self.run_cmd(cfg, options)


def main():
    logging_config = dict(ALEMBIC_LOGGING)
    logging.config.dictConfig(logging_config)
    AlembicCli().main()


if __name__ == '__main__':
    main()
