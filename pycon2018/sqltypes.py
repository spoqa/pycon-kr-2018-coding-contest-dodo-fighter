import datetime

from sqlalchemy.types import DateTime, TypeDecorator

__all__ = 'UtcDateTime',


class UtcDateTime(TypeDecorator):
    impl = DateTime(timezone=True)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, datetime.datetime):
                raise TypeError('expected datetime.datetime, not ' +
                                repr(value))
            elif value.tzinfo is None:
                raise ValueError('naive datetime is not allowed')
            return value.astimezone(datetime.timezone.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value
