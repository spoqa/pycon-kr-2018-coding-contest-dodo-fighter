import functools
import tempfile
import uuid

from flask import (Blueprint, Flask, abort, current_app as current_flask_app,
                   flash, g, jsonify, redirect, render_template, request,
                   url_for)
from flask_cdn import CDN
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from raven.contrib.flask import Sentry
from requests import get, post
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.functions import now
from werkzeug.local import LocalProxy
from werkzeug.routing import BaseConverter
from werkzeug.urls import url_decode

from .app import App
from .entities import (Match, Submission, Tournament, TournamentMatchSet,
                       TournamentMatchSetItem, User)
from .game import run_matches, run_matches_submission
from .util import build_match_tree, ngroup


current_app = LocalProxy(lambda: current_flask_app.config['APP'])
ep = Blueprint('ep', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')
login_manager = LoginManager()
cdn = CDN()


@LocalProxy
def session() -> Session:
    ctx = request._get_current_object()
    try:
        session = ctx._current_session
    except AttributeError:
        session = current_app.create_session()
        ctx._current_session = session
    return session


def close_session(exception=None):
    ctx = request._get_current_object()
    if hasattr(ctx, '_current_session'):
        s = ctx._current_session
        if exception is not None:
            s.rollback()
        s.close()


@login_manager.user_loader
def load_user(user_id: str):
    return session.query(User).filter_by(id=uuid.UUID(user_id)).one()


def ongoing_tournament_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if g.current_tournament is None:
            abort(404)
        return f(*args, **kwargs)
    return wrapper


@admin.before_request
def check_moderator():
    if not current_user.is_authenticated or not current_user.moderator:
        abort(403)


@ep.before_request
def inject_current_tournament():
    g.current_tournament = Tournament.get_current(session)


@ep.route('/')
def index():
    if g.current_tournament:
        if current_user.is_authenticated:
            submission = session.query(Submission).filter_by(
                user=current_user,
                tournament=g.current_tournament
            ).one_or_none()
        else:
            submission = None
        count = session.query(Submission).filter_by(
            tournament=g.current_tournament
        ).count()
    else:
        submission = None
        count = 0
    return render_template(
        'index.html',
        github_oauth_client_id=current_app.github_oauth_client_id,
        current_tournament=g.current_tournament,
        submission=submission, count=count
    )


@ep.route('/tournaments/<uuid:tournament_id>')
def game(tournament_id: uuid.UUID):
    tournament = session.query(Tournament).filter_by(id=tournament_id).one()
    return render_template('game.html', tournament=tournament)


@ep.route('/oauth/authorized')
def oauth_authorized():
    at_response = post('https://github.com/login/oauth/access_token', data={
        'client_id': current_app.github_oauth_client_id,
        'client_secret': current_app.github_oauth_client_secret,
        'code': request.args['code'],
        'accept': 'application/json'
    })
    assert at_response.status_code == 200
    response_data = url_decode(at_response.text)
    access_token = response_data['access_token']
    user_response = get('https://api.github.com/user',
                        params={'access_token': access_token})
    assert user_response.status_code == 200
    user_data = user_response.json()
    try:
        user = session.query(User).filter_by(
            display_name=user_data['login']
        ).one()
    except NoResultFound:
        user = User(
            display_name=user_data['login'],
            avatar=user_data['avatar_url']
        )
        session.add(user)
        session.commit()
    login_user(user)
    return redirect(url_for('.index'))


@ep.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('.index'))


@ep.route('/matches/<uuid:match_id>')
def show_match(match_id: uuid.UUID):
    match = session.query(Match).filter_by(id=match_id).one()
    if match.winner is match.p1:
        winner = 'p1'
    elif match.winner is match.p2:
        winner = 'p2'
    else:
        winner = None
    result = {
        'p1': {
            'display_name': match.p1.submission.user.display_name,
            'avatar': match.p1.submission.user.avatar
        },
        'p2': {
            'display_name': match.p2.submission.user.display_name,
            'avatar': match.p2.submission.user.avatar
        },
        'winner': winner,
        'data': match.match_data
    }
    return jsonify(**result)


@ep.route('/matches/<uuid:match_id>/disclose')
def disclose_match(match_id: uuid.UUID):
    match = session.query(Match).filter_by(id=match_id).one()
    match.disclosed = True
    session.commit()
    return jsonify(result='success')
    

@ep.route('/tournaments/<uuid:tournament_id>/submission', methods=['POST'])
@login_required
def submit(tournament_id: uuid.UUID):
    tournament = session.query(Tournament).filter_by(id=tournament_id).one()
    assert tournament.active
    file = request.files.get('script')
    if file is None:
        flash('파일을 확인해 주세요.')
        return redirect(url_for('.index'))
    with tempfile.NamedTemporaryFile() as tf:
        file.save(tf)
        tf.flush()
        try:
            winner, data = run_matches(current_app, tf.name, None)
            if winner != 0:
                flash('테스트에 통과하지 못했습니다.')
                return redirect(url_for('.index'))
        except:
            flash('코드에 오류가 있습니다.')
            return redirect(url_for('.index'))
        tf.seek(0)
        data = tf.read().decode('utf-8')
    submission = session.query(Submission).filter_by(
        user=current_user,
        tournament=tournament
    ).one_or_none()
    if submission:
        submission.code = data
        submission.created_at = now()
    else:
        submission = Submission(tournament=tournament, user=current_user,
                                code=data)
        session.add(submission)
    session.commit()
    return redirect(url_for('.index'))


@admin.route('/tournaments/<uuid:tournament_id>', methods=['GET'])
def tournament(tournament_id: uuid.UUID):
    tournament = session.query(Tournament).filter_by(
        id=tournament_id
    ).one()
    submissions_without_match = session.query(Submission).outerjoin(
        TournamentMatchSetItem
    ).filter(
        TournamentMatchSetItem.id.is_(None)
    ).order_by(Submission.created_at)
    if tournament.final_match:
        tree = build_match_tree(tournament.final_match)
    else:
        tree =None
    return render_template('admin/tournament.html', tournament=tournament,
                           submissions_without_match=submissions_without_match,
                           tree=tree, enumerate=enumerate, range=range)


@admin.route('/tournaments/<uuid:tournament_id>/match_sets',
             methods=['POST'])
def create_match_set(tournament_id: uuid.UUID):
    count = int(request.form['count']) if request.form.get('count') else 0
    tournament = session.query(Tournament).filter_by(
        id=tournament_id
    ).one()
    submissions_without_match = session.query(Submission).outerjoin(
        TournamentMatchSetItem
    ).filter(
        TournamentMatchSetItem.id.is_(None)
    ).order_by(Submission.created_at)
    if count > 0:
        submissions_without_match = submissions_without_match.limit(count)
    assert submissions_without_match.count() > 0
    set = TournamentMatchSet(tournament=tournament)
    items = [TournamentMatchSetItem(
        tournament_match_set=set, submission=s
    ) for s in submissions_without_match]
    session.add(set)
    session.add_all(items)
    session.commit()
    return redirect(url_for('.tournament', tournament_id=tournament_id))


@admin.route('/submissions/<uuid:submission_id>')
def submission(submission_id: uuid.UUID):
    submission = session.query(Submission).filter_by(id=submission_id).one()
    return render_template('admin/submission.html', submission=submission)


@admin.route('/match_sets/<uuid:set_id>')
def match_set(set_id: uuid.UUID):
    mset = session.query(TournamentMatchSet).filter_by(id=set_id).one()
    if not mset.final_match:
        abort(404)
    return render_template('admin/match_set.html', match_set=mset,
                           tree=build_match_tree(mset.final_match),
                           range=range)


@admin.route('/match_sets/<uuid:set_id>/create_match')
def create_matches(set_id: uuid.UUID):
    mset = session.query(TournamentMatchSet).filter_by(id=set_id).one()
    if mset.final_match:
        return redirect(url_for('.tournament',
                                tournament_id=mset.tournament.id))
    subs = [(i, None) for i in mset.items]
    level = 0
    match = None
    while len(subs) > 1:
        pairs = ngroup(2, subs, fillvalue=(None, None))
        nsubs = []
        for pair in pairs:
            print(pair)
            match = Match(
                p1=pair[0][0],
                p2=pair[1][0],
                p1_parent=pair[0][1],
                p2_parent=pair[1][1],
                iteration=level,
                match_data=[]
            )
            if pair[0][0] is not None and pair[1][0] is not None:
                winner, data = run_matches_submission(
                    current_app, pair[0][0].submission, pair[1][0].submission
                )
                if winner is not None:
                    nsubs.append((pair[winner][0], match))
                    wm = pair[winner][0]
                else:
                    nsubs.append((None, match))
                    wm = None
                match.match_data = data
            else:
                if pair[0][0]:
                    nsubs.append((pair[0][0], match))
                    wm = pair[0][0]
                elif pair[1][0]:
                    nsubs.append((pair[1][0], match))
                    wm = pair[1][0]
                else:
                    subs.append((None, match))
                    wm = None
            match.winner = wm
            session.add(match)
        level += 1
        subs.clear()
        subs.extend(nsubs)
    if len(subs) == 1 and match:
        mset.final_match = match
        session.commit()
    else:
        abort(500)
    return redirect(url_for('.tournament', tournament_id=mset.tournament.id))


@admin.route('/tournaments/<uuid:tournament_id>/create_matches')
def finalize_matches(tournament_id: uuid.UUID):
    tournament = session.query(Tournament).filter_by(id=tournament_id).one()
    for match_set in tournament.match_sets:
        if match_set.final_match is None:
            abort(400)
    level = 0
    msets = [(i, None) for i in tournament.match_sets]
    while len(msets) > 1:
        pairs = ngroup(2, msets, fillvalue=(None, None))
        lmsets = []
        for pair in pairs:
            match = Match(
                p1=pair[0][0].final_match.winner,
                p2=pair[1][0].final_match.winner,
                p1_parent=pair[0][1],
                p2_parent=pair[1][1],
                iteration=level,
                match_data=[]
            )
            if pair[0][0] is not None and pair[1][0] is not None:
                winner, data = run_matches_submission(
                    current_app,
                    pair[0][0].final_match.winner.submission,
                    pair[1][0].final_match.winner.submission
                )
                if winner is not None:
                    lmsets.append((pair[winner][0], match))
                    wm = pair[winner][0].final_match.winner
                else:
                    lmsets.append((None, match))
                    wm = None
                match.match_data = data
            else:
                if pair[0][0]:
                    lmsets.append((pair[0][0], match))
                    wm = pair[0][0].final_match.winner
                elif pair[1][0]:
                    lmsets.append((pair[1][0], match))
                    wm = pair[1][0].final_match.winner
                else:
                    lmsets.append((None, match))
                    wm = None
            match.winner = wm
            session.add(match)
        level += 1
        msets.clear()
        msets.extend(lmsets)
    if len(msets) == 1 and match:
        tournament.final_match = match
        session.commit()
    else:
        abort(500)
    return redirect(url_for('.tournament', tournament_id=tournament.id))


@admin.route('/match_sets/<uuid:set_id>/clear')
def clear_matches(set_id: uuid.UUID):
    mset = session.query(TournamentMatchSet).filter_by(id=set_id).one()
    if not mset.tournament.final_match:
        tmsis = [x.id for x in session.query(TournamentMatchSetItem).filter(
            TournamentMatchSetItem.tournament_match_set == mset
        )]
        mset.final_match = None
        session.flush()
        session.query(Match).filter(or_(
            Match.p1_id.in_(tmsis), Match.p2_id.in_(tmsis)
        )).delete(synchronize_session='fetch')
        session.commit()
    return redirect(url_for('.tournament', tournament_id=mset.tournament.id))


def create_web_app(app: App) -> Flask:
    wsgi = Flask(__name__)
    wsgi.register_blueprint(ep)
    wsgi.register_blueprint(admin)
    wsgi.teardown_request(close_session)
    wsgi.config['APP'] = app
    wsgi.secret_key = app.secret_key
    login_manager.init_app(wsgi)
    cdn.init_app(wsgi)
    if app.sentry_dsn:
        Sentry(wsgi, dsn=app.sentry_dsn)
    return wsgi

