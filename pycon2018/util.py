import itertools
import os
import stat
import tempfile
import typing

from .entities import Match


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
