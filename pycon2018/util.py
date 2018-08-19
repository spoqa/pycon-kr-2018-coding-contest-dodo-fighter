import collections
import datetime
import functools
import itertools
import os
import stat
import string
import tempfile
import typing

from sqlalchemy.orm import Session


def ngroup(n: int, iterable: typing.Iterable[typing.Any], fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def build_match_tree(
        session: Session, terminal, final: bool, full_disclosure: bool
) -> typing.Mapping[int, typing.Any]:
    matches_by_iteration = {}
    result = []

    def traverse(node):
        if node.iteration not in matches_by_iteration:
            matches_by_iteration[node.iteration] = []
        matches_by_iteration[node.iteration].append(node)
        if node.p1_parent:
            traverse(node.p1_parent)
        if node.p2_parent:
            traverse(node.p2_parent)
    traverse(terminal)
    group_disclosed = True
    if final:
        group_names = get_match_set_group_names(session,
                                                terminal.match_set.tournament)
    for i in range(terminal.iteration + 1):
        matches = matches_by_iteration[i]
        for match in matches:
            item = {
                'id': str(match.id),
                'round': 2 ** (terminal.iteration + 1 - match.iteration),
                'p1': '?',
                'p1_group': None,
                'p2': '?',
                'p2_group': None,
                'winner': '?'
            }
            if match.disclosed or group_disclosed or full_disclosure:
                if match.p1:
                    item['p1'] = match.p1.submission.user.display_name
                    if final:
                        item['p1_group'] = group_names[
                            match.p1.tournament_match_set.id
                        ]
                else:
                    item['p1'] = None
                if match.p2:
                    item['p2'] = match.p2.submission.user.display_name
                    if final:
                        item['p2_group'] = group_names[
                            match.p2.tournament_match_set.id
                        ]
                else:
                    item['p2'] = None
            if match.disclosed or full_disclosure:
                if match.winner:
                    item['winner'] = match.winner.submission.user.display_name
                else:
                    item['winner'] = None
            result.append(item)
        group_disclosed = all(map(lambda x: x.disclosed, matches))
    return result


def make_tempfile_public(temp: tempfile.TemporaryFile):
    os.chmod(
        temp.name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    )


def get_match_set_group_names(
    session: Session, tournament
) -> collections.OrderedDict:
    from .entities import Tournament, TournamentMatchSet
    az = string.ascii_uppercase
    query = session.query(TournamentMatchSet.id).filter_by(
        tournament=tournament
    ).order_by(TournamentMatchSet.created_at.asc())
    result = collections.OrderedDict()
    for index, (id, ) in enumerate(query):
        if index >= len(az):
            name = az[index // len(az)] + az[index % len(az)]
        else:
            name = az[index]
        result[id] = name
    return result


utcnow = functools.partial(datetime.datetime.now, datetime.timezone.utc)
