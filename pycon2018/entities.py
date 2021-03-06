import uuid

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import backref, object_session, relationship
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Boolean, Integer, String, Text, Unicode
from sqlalchemy_utils import UUIDType

from .orm import Base
from .sqltypes import UtcDateTime
from .util import utcnow


class User(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    display_name = Column(Unicode(128), nullable=False, unique=True)
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
    begin_at = Column(UtcDateTime, nullable=False)
    finish_at = Column(UtcDateTime, nullable=False)

    final_match_id = Column(UUIDType, ForeignKey('match.id'))
    final_match = relationship('Match', uselist=False)

    @property
    def active(self) -> bool:
        return self.begin_at <= utcnow() < self.finish_at

    @classmethod
    def get_current(cls, session):
        return session.query(cls).filter(
            cls.begin_at <= utcnow(),
            utcnow() < cls.finish_at
        ).first()

    __tablename__ = 'tournament'


class Audit(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    user_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    user = relationship(User, uselist=False, lazy='joined')

    code = Column(Text, nullable=False)

    created_at = Column(UtcDateTime, nullable=False,
                        default=utcnow,
                        index=True)

    __tablename__ = 'audit'


class Submission(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    tournament_id = Column(UUIDType, ForeignKey(Tournament.id),
                           nullable=False)
    tournament = relationship(Tournament, uselist=False)

    user_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    user = relationship(User, uselist=False, lazy='joined')

    code = Column(Text, nullable=False)

    created_at = Column(UtcDateTime, nullable=False,
                        default=utcnow)

    __table_args__ = (
        UniqueConstraint('tournament_id', 'user_id',
                         name='uc_submission'),
    )
    __tablename__ = 'submission'


class TournamentMatchSet(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    created_at = Column(UtcDateTime, nullable=False, default=utcnow)

    tournament_id = Column(UUIDType, ForeignKey(Tournament.id),
                           nullable=False)
    tournament = relationship(
        Tournament, uselist=False,
        backref=backref('match_sets', order_by='TournamentMatchSet.created_at')
    )

    final_match_id = Column(UUIDType, ForeignKey('match.id'))
    final_match = relationship('Match', uselist=False)

    @property
    def group_name(self):
        from .util import get_match_set_group_names
        session = object_session(self)
        gns = get_match_set_group_names(session, self.tournament)
        if self.id in gns:
            return gns[self.id]
        return None

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

    p1_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id))
    p1 = relationship(TournamentMatchSetItem, foreign_keys=[p1_id],
                      uselist=False, lazy='joined')

    p1_parent_id = Column(UUIDType, ForeignKey('match.id'))
    p1_child = relationship('Match', foreign_keys=[p1_parent_id],
                            backref=backref('p1_parent', remote_side=[id]),
                            uselist=False)

    p2_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id))
    p2 = relationship(TournamentMatchSetItem, foreign_keys=[p2_id],
                      uselist=False, lazy='joined')

    p2_parent_id = Column(UUIDType, ForeignKey('match.id'))
    p2_child = relationship('Match', foreign_keys=[p2_parent_id],
                            backref=backref('p2_parent', remote_side=[id]),
                            uselist=False)

    winner_id = Column(UUIDType, ForeignKey(TournamentMatchSetItem.id))
    winner = relationship(TournamentMatchSetItem, foreign_keys=[winner_id],
                          uselist=False)

    iteration = Column(Integer, nullable=False)
    match_data = Column(JSON, nullable=False)
    disclosed = Column(Boolean, nullable=False, default=False)

    @property
    def terminal(self):
        child = self
        while child.p1_child or child.p2_child:
            child = child.p1_child or child.p2_child
        return child

    @property
    def match_set(self) -> TournamentMatchSet:
        assert self.p1 or self.p2, f'Match {self} has no players.'
        if self.p1:
            return self.p1.tournament_match_set
        else:
            return self.p2.tournament_match_set

    __tablename__ = 'match'
