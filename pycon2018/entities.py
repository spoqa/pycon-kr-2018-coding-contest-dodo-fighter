import datetime
import uuid

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import backref, object_session, relationship
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.functions import now
from sqlalchemy.types import Boolean, DateTime, Integer, String, Text, Unicode
from sqlalchemy_utils import UUIDType

from .orm import Base


class User(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    email = Column(String(128), nullable=False, unique=True)
    display_name = Column(Unicode(128), nullable=False)
    avatar = Column(String(256))
    moderator = Column(Boolean, nullable=False, default=False)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    __tablename__ = 'user'


class Tournament(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    begin_at = Column(DateTime, nullable=False)
    finish_at = Column(DateTime, nullable=False)
    
    final_match_id = Column(UUIDType, ForeignKey('match.id'))
    final_match = relationship('Match', uselist=False)

    @property
    def active(self) -> bool:
        return self.begin_at <= datetime.datetime.now() < self.finish_at

    @classmethod
    def get_current(cls, session):
        return session.query(cls).filter(
            cls.begin_at <= now(),
            now() < cls.finish_at
        ).first()

    __tablename__ = 'tournament'


class Submission(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    
    tournament_id = Column(UUIDType, ForeignKey(Tournament.id),
                           nullable=False)
    tournament = relationship(Tournament, uselist=False)

    user_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    user = relationship(User, uselist=False, lazy='joined')

    code = Column(Text, nullable=False)

    created_at = Column(DateTime, nullable=False,
                        default=datetime.datetime.now)

    __table_args__ = (
        UniqueConstraint('tournament_id', 'user_id',
                         name='uc_submission'),
    )
    __tablename__ = 'submission'


class TournamentMatchSet(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    created_at = Column(DateTime, nullable=False,
                        default=datetime.datetime.now)

    tournament_id = Column(UUIDType, ForeignKey(Tournament.id),
                           nullable=False)
    tournament = relationship(
        Tournament, uselist=False,
        backref=backref('match_sets', order_by='TournamentMatchSet.created_at')
    )

    final_match_id = Column(UUIDType, ForeignKey('match.id'))
    final_match = relationship('Match', uselist=False)

    __tablename__ = 'tournament_match_set'


class TournamentMatchSetItem(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    tournament_match_set_id = Column(UUIDType,
                                     ForeignKey(TournamentMatchSet.id),
                                     nullable=False)
    tournament_match_set = relationship(TournamentMatchSet, uselist=False,
                                        backref='items')

    submission_id = Column(UUIDType, ForeignKey(Submission.id),
                           nullable=False, unique=True)
    submission = relationship(Submission, uselist=False,
                              backref=backref('match_item', uselist=False),
                              lazy='joined')

    __tablename__ = 'tournament_match_set_item'


class Match(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    p1_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id),
                nullable=False)
    p1 = relationship(TournamentMatchSetItem, foreign_keys=[p1_id],
                      uselist=False, lazy='joined')

    p1_parent_id = Column(UUIDType, ForeignKey('match.id'))
    p1_parent = relationship('Match', foreign_keys=[p1_parent_id],
                             uselist=False)

    p2_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id),
                   nullable=False)
    p2 = relationship(TournamentMatchSetItem, foreign_keys=[p2_id],
                      uselist=False, lazy='joined')

    p2_parent_id = Column(UUIDType, ForeignKey('match.id'))
    p2_parent = relationship('Match', foreign_keys=[p2_parent_id],
                             uselist=False)

    winner_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id))
    winner = relationship(TournamentMatchSetItem, foreign_keys=[winner_id],
                          uselist=False)

    iteration = Column(Integer, nullable=False)
    match_data = Column(JSON, nullable=False)
    disclosed = Column(Boolean, nullable=False, default=False)

    __tablename__ = 'match'
