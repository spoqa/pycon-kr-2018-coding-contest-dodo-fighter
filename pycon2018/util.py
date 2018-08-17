import collections
import itertools
import os
import stat
import string
import tempfile
import typing

from sqlalchemy.orm import Session

from .entities import Match, Tournament, TournamentMatchSet


def ngroup(n: int, iterable: typing.Iterable[typing.Any], fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def build_match_tree(terminal: Match) -> typing.Mapping[int, typing.Any]:
    result = {}

    def traverse(node: Match):
        if node.iteration not in result:
            result[node.iteration] = []
        result[node.iteration].append(node)
        if node.p1_parent:
            traverse(node.p1_parent)
        if node.p2_parent:
            traverse(node.p2_parent)
    traverse(terminal)
    return result


def make_tempfile_public(temp: tempfile.TemporaryFile):
    os.chmod(
        temp.name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    )


def get_match_set_group_names(
        session: Session, tournament: Tournament
) -> collections.OrderedDict:
    az = string.ascii_uppercase
    query = sesion.query(TournamentMatchSetItem.id).filter_by(
        tournament=tournament
    ).order_by(TournamentMatchSetItem.created_at.asc())
    result = collections.OrderedDict()
    for index, (item, ) in enumerate(query):
        if index >= len(az):
            name = az[index // len(az)] + az[index % len(z)]
        else:
            name = az[index]
        result[i.id] = name
    return result
