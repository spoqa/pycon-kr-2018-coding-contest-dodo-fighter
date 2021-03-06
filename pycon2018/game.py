import collections
import enum
import json
import random
import subprocess
import typing

from .app import App


class Action(enum.Enum):
    idle = 'idle'
    forward = 'forward'
    backward = 'backward'
    punch = 'punch'
    kick = 'kick'
    crouch = 'crouch'
    jump = 'jump'
    guard = 'guard'


class Agent:

    def __init__(self):
        self.reset_with(0, 0)

    def reset_with(self, player_number: int, position: int):
        self.player_number = player_number
        self.initial_position = position
        self.reset()

    def reset(self):
        self.health = 100
        self.last_action = None
        self.last_inflicted_damage = 0
        self.position = self.initial_position
        self.previous_actions = collections.deque(maxlen=5)
        self.guard_count = 0

    def distance(self, opponent):
        return abs(opponent.position - self.position)

    def build_payload(self, opponent, match_records: typing.Sequence[str],
                      time_left: int) -> typing.Mapping[str, typing.Any]:
        return {
            'distance': self.distance(opponent),
            'time_left': time_left,
            'health': self.health,
            'opponent_health': opponent.health,
            'opponent_action': (
                opponent.last_action.value if opponent.last_action else None
            ),
            'given_damage': self.last_inflicted_damage,
            'taken_damage': opponent.last_inflicted_damage,
            'match_records': [
                x == self.player_number if x is not None else None
                for x in match_records
            ],
        }

    def get_action(self, opponent, match_records: typing.Sequence[str],
                   time_left: int) -> Action:
        action = self._get_action(opponent, match_records, time_left)
        self.last_action = action
        self.previous_actions.append(action)
        return action

    def _get_action(self, opponent, match_records: typing.Sequence[str],
                    time_left: int) -> Action:
        raise NotImplementedError

    def damage_modifier(self, damage: int):
        ua = set(self.previous_actions)
        if len(ua) == 1 and len(self.previous_actions) >= 3:
            action_diversity_multiplier = 1 / 3
        elif len(ua) == 2 and len(self.previous_actions) >= 3:
            action_diversity_multiplier = 2 / 3
        else:
            action_diversity_multiplier = 1.0
        guard_multiplier = 1.25 ** self.guard_count
        return int(damage * action_diversity_multiplier * guard_multiplier)

    def inflict_damage(self, opponent, damage: int):
        damage = self.damage_modifier(damage)
        opponent.health = max(0, opponent.health - damage)
        self.last_inflicted_damage = damage
        self.guard_count = 0

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        pass


class FixedAgent(Agent):

    def __init__(self, action: Action):
        super(FixedAgent, self).__init__()
        self.action = action

    def _get_action(self, opponent, match_records: typing.Sequence[str],
                    time_left: int) -> Action:
        return self.action


class RandomAgent(Agent):

    choices = list(Action.__members__.values())

    def _get_action(self, opponent, match_records: typing.Sequence[str],
                    time_left: int) -> Action:
        return random.choice(self.choices)


class ScriptException(Exception):

    def __init__(self, message: str, output: str):
        super(ScriptException, self).__init__(message)
        self.message = message
        self.output = output

    def __str__(self):
        return f'{super(ScriptException, self).__str__()}: {self.output}'


class ExternalScriptAgent(Agent):

    def __init__(self, app: App, path: str):
        super(ExternalScriptAgent, self).__init__()
        self.handle = None
        self.path = path
        self.error = False
        self.open_subprocess(app)

    def open_subprocess(self, app):
        if self.handle is not None:
            self.handle.terminate()
        self.handle = subprocess.Popen([app.game_evaluator_path, self.path],
                                       stdout=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

    def reinitiate(self, app):
        if self.error:
            self.open_subprocess(app)
            self.error = False

    def _get_action(self, opponent, match_records: typing.Sequence[str],
                    time_left: int) -> Action:
        payload = json.dumps(self.build_payload(opponent, match_records,
                                                time_left))
        try:
            self.handle.stdin.write(payload.encode('utf-8'))
            self.handle.stdin.write(b'\n')
            self.handle.stdin.flush()
        except Exception:
            err = self.handle.stderr.read(1024).decode('utf-8')
            self.error = True
            raise ScriptException('Broken pipe.', err)
        action = self.handle.stdout.readline().decode('utf-8').strip()
        if not action:
            err = self.handle.stderr.read(1024).decode('utf-8')
            self.error = True
            raise ScriptException('Unexpected end of file.', err)
        try:
            return Action(action)
        except ValueError:
            self.error = True
            raise ScriptException(f'Unknown action {action}', None)

    def __exit__(self, exception_type, exception_value, traceback):
        if self.handle is not None:
            self.handle.terminate()


def evaluate(app: App, p1: Agent, p2: Agent,
             match_records: typing.Sequence[str], raise_: bool=False):
    record = []
    time_left = app.game_round_time

    p1.reset_with(0, app.game_p1_initial_position)
    p2.reset_with(1, app.game_p2_initial_position)

    def put_record(action: str, **kwargs):
        record.append({
            'action': action, 'time': time_left,
            'p1': {'health': p1.health, 'position': p1.position},
            'p2': {'health': p2.health, 'position': p2.position},
            **kwargs})

    while time_left >= 0:
        try:
            p1a = p1.get_action(p2, match_records, time_left)
        except ScriptException:
            if raise_:
                raise
            p1_failed = True
        else:
            p1_failed = False
        try:
            p2a = p2.get_action(p1, match_records, time_left)
        except ScriptException:
            if raise_:
                raise
            p2_failed = True
        else:
            p2_failed = False
        if p1_failed and p2_failed:
            put_record('both_error')
            return None, record
        elif p1_failed:
            put_record('p1_error')
            return 1, record
        elif p2_failed:
            put_record('p2_error')
            return 0, record
        p1.last_inflicted_damage = 0
        p2.last_inflicted_damage = 0
        p1_idle = True
        p2_idle = True
        if p1a is Action.forward:
            if p2.position > p1.position:
                p1.position += 1
            put_record('p1_forward')
            p1_idle = False
        elif p1a is Action.backward:
            if p1.position >= p1.initial_position - 2:
                p1.position -= 1
            put_record('p1_backward')
            p1_idle = False
        if p2a is Action.forward:
            if p2.position > p1.position:
                p2.position -= 1
            put_record('p2_forward')
            p2_idle = False
        elif p2a is Action.backward:
            if p2.position <= p2.initial_position + 2:
                p2.position += 1
            put_record('p2_backward')
            p2_idle = False
        if p1a is Action.punch:
            if p1.distance(p2) > 0:
                put_record('p1_punch_unreachable')
            elif p2a is Action.crouch:
                p2.guard_count += 2
                put_record('p1_punch_avoid')
            elif p2a is Action.guard:
                damage = random.randrange(*app.game_hit_point_guard_range)
                p2.guard_count += 1
                p1.inflict_damage(p2, damage)
                put_record('p1_punch_guard', damage=damage)
            else:
                damage = random.randrange(*app.game_hit_point_range)
                p1.inflict_damage(p2, damage)
                put_record('p1_punch', damage=damage)
            p1_idle = False
        elif p1a is Action.kick:
            if p1.distance(p2) > 0:
                put_record('p1_kick_unreachable')
            elif p2a is Action.jump:
                p2.guard_count += 2
                put_record('p1_kick_avoid')
            elif p2a is Action.guard:
                damage = random.randrange(*app.game_hit_point_guard_range)
                p2.guard_count += 1
                p1.inflict_damage(p2, damage)
                put_record('p1_kick_guard', damage=damage)
            else:
                damage = random.randrange(*app.game_hit_point_range)
                p1.inflict_damage(p2, damage)
                put_record('p1_kick', damage=damage)
            p1_idle = False
        if p2.health <= 0:
            put_record('p1_victory_ko')
            return 0, record
        if p2a is Action.punch:
            if p2.distance(p1) > 0:
                put_record('p2_punch_unreachable')
            elif p1a is Action.crouch:
                p1.guard_count += 2
                put_record('p2_punch_avoid')
            elif p1a is Action.guard:
                damage = random.randrange(*app.game_hit_point_guard_range)
                p1.guard_count += 1
                p2.inflict_damage(p1, damage)
                put_record('p2_punch_guard', damage=damage)
            else:
                damage = random.randrange(*app.game_hit_point_range)
                p2.inflict_damage(p1, damage)
                put_record('p2_punch', damage=damage)
            p2_idle = False
        elif p2a is Action.kick:
            if p2.distance(p1) > 0:
                put_record('p2_kick_unreachable')
            elif p1a is Action.jump:
                p1.guard_count += 2
                put_record('p2_kick_avoid')
            elif p1a is Action.guard:
                damage = random.randrange(*app.game_hit_point_guard_range)
                p1.guard_count += 1
                p2.inflict_damage(p1, damage)
                put_record('p2_kick_guard', damage=damage)
            else:
                damage = random.randrange(*app.game_hit_point_range)
                p2.inflict_damage(p1, damage)
                put_record('p2_kick', damage=damage)
            p2_idle = False
        if p1.health <= 0:
            put_record('p2_victory_ko')
            return 1, record
        if p1_idle and p2_idle:
            put_record('idle')
        time_left -= 1
    if time_left < 0:
        time_left = 0
    if p1.health == p2.health:
        put_record('draw')
        return None, record
    elif p1.health > p2.health:
        put_record('p1_victory_time_over')
        return 0, record
    else:
        put_record('p2_victory_time_over')
        return 1, record


def run_matches(app: App,
                p1: typing.Union[Agent, str],
                p2: typing.Union[Agent, str],
                raise_: bool=False):
    data = []
    wins = [0, 0]
    if isinstance(p1, str):
        p1a = ExternalScriptAgent(app, p1)
    elif not isinstance(p1, Agent):
        raise TypeError('p1 should be an agent or a string')
    else:
        p1a = p1
    if isinstance(p2, str):
        p2a = ExternalScriptAgent(app, p2)
    elif not isinstance(p2, Agent):
        raise TypeError('p2 should be an agent or a string')
    else:
        p2a = p2
    with p1a, p2a:
        match_records = []
        for i in range(app.game_round_count):
            winner, matchdata = evaluate(app, p1a, p2a, match_records, raise_)
            data.append(matchdata)
            match_records.append(winner)
            if winner is not None:
                wins[winner] += 1
            max_wins_user = app.game_round_count - 1
            if wins[0] == max_wins_user or wins[1] == max_wins_user:
                break
            if isinstance(p1a, ExternalScriptAgent) and p1a.error:
                p1a.reinitiate(app)
            if isinstance(p2a, ExternalScriptAgent) and p2a.error:
                p2a.reinitiate(app)
    if wins[0] == wins[1]:
        return None, data
    elif wins[0] > wins[1]:
        return 0, data
    else:
        return 1, data


def test():
    import pprint
    import sys
    app = App()
    if len(sys.argv) >= 3:
        if sys.argv[2] == 'random':
            p2 = RandomAgent()
        else:
            p2 = sys.argv[2]
    else:
        p2 = FixedAgent(Action.idle)
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'random':
            p1 = RandomAgent()
        else:
            p1 = sys.argv[1]
    else:
        p1 = FixedAgent(Action.idle)
    winner, data = run_matches(app, p1, p2, raise_=True)
    pprint.pprint(data)
    print(winner)


if __name__ == '__main__':
    test()
