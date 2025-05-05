from flask import render_template, flash, redirect, url_for, request, session
from app import app, engine, Session
from sqlalchemy import text, func, case
from app.forms import LoginForm, RegisterForm
from werkzeug.security import check_password_hash, generate_password_hash
import random
from flask_login import login_user, logout_user, current_user, login_required
from app.trivia_questions import generate_player_stat_question, generate_team_performance_question
from app.baseball_wordle import BaseballWordle
from datetime import datetime, date
import json
from app.baseball_connections import BaseballConnections
import time
from app.baseball_strands import BaseballStrands
from app.baseball_crossword import BaseballCrossword
from app.models import (
    User,
    TriviaScore,
    WordleScore,
    ConnectionsScore,
    StrandsScore,
    CrosswordPuzzle,
    CrosswordScore,
    CrosswordWordUsage,
    CrosswordHint
)
from flask_login import login_required, current_user
from app import app, Session


@app.route('/')
@app.route('/index')
def index():
    games = [
        {
            'name': 'Baseball Trivia',
            'description': 'Test your baseball knowledge with multiple choice questions',
            'url': url_for('trivia'),
            'icon': '⚾'
        },
        {
            'name': 'Baseball Wordle',
            'description': 'Guess the 5-letter baseball player name',
            'url': url_for('baseball_wordle'),
            'icon': '📝'
        },
        {
            'name': 'Baseball Connections',
            'description': 'Group related baseball terms together',
            'url': url_for('baseball_connections'),
            'icon': '🔗'
        },
        {
            'name': 'Baseball Strands',
            'description': 'Find hidden baseball words in the grid',
            'url': url_for('baseball_strands'),
            'icon': '🔍'
        },
        {
            'name': 'Baseball Crossword',
            'description': 'Solve the daily baseball-themed crossword puzzle',
            'url': url_for('baseball_crossword'),
            'icon': '🔤'
        }
    ]

    user_stats = None
    if current_user.is_authenticated:
        with Session() as session_db:
            trivia_count = session_db.query(TriviaScore).filter_by(user_id=current_user.id).count()
            wordle_count = session_db.query(WordleScore).filter_by(user_id=current_user.id).count()
            connections_count = session_db.query(ConnectionsScore).filter_by(user_id=current_user.id).count()
            strands_count = session_db.query(StrandsScore).filter_by(user_id=current_user.id).count()
            crossword_count = session_db.query(CrosswordScore).filter_by(user_id=current_user.id).count()

            user_stats = {
                'trivia_rounds': trivia_count,
                'wordle_games': wordle_count,
                'connections_games': connections_count,
                'strands_games': strands_count,
                'crossword_games': crossword_count
            }

    return render_template('index.html', games=games, user_stats=user_stats)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied: Admins only.")
        return redirect(url_for('index'))

    with Session() as session_db:
        users = session_db.query(User).all()
        for user in users:
            session_db.expunge(user)
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/toggle_ban/<int:user_id>', methods=['POST'])
@login_required
def toggle_ban(user_id):
    if not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('index'))

    with Session() as session_db:
        user = session_db.query(User).filter_by(id=user_id).first()
        if user:
            user.is_banned = not user.is_banned
            session_db.commit()
            flash(f"User {user.username} ban status updated.")
        else:
            flash("User not found.")
    return redirect(url_for('admin_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with Session() as session_db:
            user = session_db.query(User).filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                if user.is_banned:
                    flash("This user is banned.")
                    return redirect(url_for('login'))
                else:
                    session_db.expunge(user)  # Detach before login
                    login_user(user)
                    flash(f'Welcome, {user.username}!')
                    if user.is_admin:
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('index'))
            else:
                flash("Invalid username or password.")
                return redirect(url_for('login'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()

    # Clear all game states
    game_states = ['connections_state', 'strands_state', 'wordle_state', 'crossword_state',
                   'question_count', 'score', 'correct_answers',
                   'round_number', 'asked_question_ids', 'wordle_difficulty',
                   'question_data']

    for state in game_states:
        if state in session:
            session.pop(state)

    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        with Session() as session_db:
            hashed_pw = generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password_hash=hashed_pw, is_admin=False, is_banned=False)
            session_db.add(new_user)
            session_db.commit()
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/trivia', methods=['GET', 'POST'])
def trivia():
    try:
        with Session() as session_db:
            session.setdefault('question_count', 0)
            session.setdefault('score', 0)
            session.setdefault('correct_answers', 0)
            session.setdefault('asked_question_ids', [])

            latest_score = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(
                TriviaScore.round_number.desc()).first()
            current_round_number = (latest_score.round_number + 1) if latest_score else 1
            session['round_number'] = current_round_number

            if session['question_count'] >= 10:
                correct_answers = session['correct_answers']
                score = session['score']

                new_score = TriviaScore(
                    user_id=current_user.id,
                    score=score,
                    total_attempted=10,
                    correct_answers=correct_answers,
                    percentage=round((correct_answers / 10) * 100, 2),
                    round_number=session['round_number']
                )
                session_db.add(new_score)
                session_db.commit()

                session['question_count'] = 0
                session['score'] = 0
                session['correct_answers'] = 0
                session['round_number'] += 1
                session['asked_question_ids'] = []

                return redirect(url_for('trivia_results'))

            if request.method == 'GET' or 'question_data' not in session:  # Generate question on GET or if not in session
                question_data = None
                for _ in range(5):
                    generator = random.choice([generate_player_stat_question, generate_team_performance_question])
                    question_data = generator(session_db, session.get('asked_question_ids', []))
                    if question_data:
                        break

                if not question_data:
                    flash("Sorry, we couldn't generate a trivia question right now. Please try again later.")
                    return redirect(url_for('trivia'))

                session['question_data'] = question_data  # Store in session

            if request.method == 'POST':
                user_answer = request.form.get('answer')

                # Get question data from session
                question_data = session.pop('question_data')  # Remove from session after use

                if user_answer == question_data['correct_letter']:
                    flash("Correct! 🎉")
                    session['score'] += 1
                    session['correct_answers'] += 1
                else:
                    correct_answer_text = question_data['correct_answer']
                    flash(f"Wrong. The correct answer was {question_data['correct_letter']}) {correct_answer_text}")

                session['question_count'] += 1
                session['asked_question_ids'].append(question_data['question_id'])
                return redirect(url_for('trivia'))

            return render_template(
                'trivia.html',
                question=session['question_data']['question'],  # Get question from session
                options=session['question_data']['options'],  # Get options from session
                question_number=session['question_count'] + 1
            )

    except Exception as e:
        flash("An unexpected error occurred. Please try again.")
        return redirect(url_for('index'))


@app.route('/trivia/results')
def trivia_results():
    with Session() as session_db:
        # Get the latest score for the user
        latest_score = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(
            TriviaScore.round_number.desc()).first()

        if latest_score:
            score = latest_score.score
            total_attempted = latest_score.total_attempted
            correct_answers = latest_score.correct_answers
            percentage = latest_score.percentage
            round_number = latest_score.round_number
        else:
            score = total_attempted = correct_answers = percentage = round_number = 0

        # Get top 10 rounds
        rounds = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(
            TriviaScore.score.desc()).limit(10).all()

        # Create a list of dictionaries with the data we need instead of expunging
        rounds_data = []
        for round in rounds:
            rounds_data.append({
                'round_number': round.round_number,
                'score': round.score,
                'total_attempted': round.total_attempted,
                'correct_answers': round.correct_answers,
                'percentage': round.percentage
            })

        # Create latest score dictionary if it exists
        latest_score_data = None
        if latest_score:
            latest_score_data = {
                'round_number': latest_score.round_number,
                'score': latest_score.score,
                'total_attempted': latest_score.total_attempted,
                'correct_answers': latest_score.correct_answers,
                'percentage': latest_score.percentage
            }

    return render_template(
        'results.html',
        title='Your Trivia Results',
        latest_score=latest_score_data,
        rounds=rounds_data
    )
@app.route('/wordle', methods=['GET', 'POST'])
@login_required
def baseball_wordle():
    wordle = BaseballWordle()

    # Check if it's a new day
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    # Handle difficulty selection
    if request.method == 'POST' and 'difficulty' in request.form:
        session['wordle_difficulty'] = request.form['difficulty']
        session['wordle_state'] = None  # Reset game with new difficulty
        return redirect(url_for('baseball_wordle'))

    # Get current difficulty
    difficulty = session.get('wordle_difficulty', 'medium')

    if session.get('wordle_date') != today_str:
        session['wordle_state'] = None
        session['wordle_date'] = today_str

    # Initialize or load game state
    if 'wordle_state' not in session or session['wordle_state'] is None:
        with Session() as session_db:
            target_word = wordle.get_word_by_difficulty(session_db, difficulty)

        session['wordle_state'] = {
            'target_word': target_word,
            'guesses': [],
            'attempts': 0,
            'solved': False,
            'feedback': [],
            'difficulty': difficulty
        }

    state = session['wordle_state']

    # Get appropriate hint based on attempts
    hint = None
    if state['attempts'] >= 3 and not state['solved']:
        with Session() as session_db:
            hint = wordle.get_player_hint(session_db, state['target_word'], state['attempts'])

    if request.method == 'POST' and 'guess' in request.form:
        guess = request.form.get('guess', '').upper()

        if len(guess) == 5 and guess.isalpha() and not state['solved']:
            feedback = wordle.check_guess(guess, state['target_word'])
            state['guesses'].append(guess)
            state['feedback'].append(feedback)
            state['attempts'] += 1

            if guess == state['target_word']:
                state['solved'] = True
                flash(f"Congratulations! You found {state['target_word']}!")

                # Save score to database
                with Session() as session_db:
                    score = WordleScore(
                        user_id=current_user.id,
                        word=state['target_word'],
                        attempts=state['attempts'],
                        solved=True,
                        date_played=datetime.utcnow(),
                        game_state=json.dumps(state)
                    )
                    session_db.add(score)
                    session_db.commit()

            elif state['attempts'] >= wordle.max_attempts:
                flash(f"Game over! The word was {state['target_word']}")

                # Save incomplete game
                with Session() as session_db:
                    score = WordleScore(
                        user_id=current_user.id,
                        word=state['target_word'],
                        attempts=state['attempts'],
                        solved=False,
                        date_played=datetime.utcnow(),
                        game_state=json.dumps(state)
                    )
                    session_db.add(score)
                    session_db.commit()

            session['wordle_state'] = state
            return redirect(url_for('baseball_wordle'))

    return render_template('wordle.html',
                           state=state,
                           max_attempts=wordle.max_attempts,
                           hint=hint,
                           current_difficulty=difficulty)

@app.route('/wordle/stats')
@login_required
def wordle_stats():
    with Session() as session_db:
        stats = session_db.query(
            func.count(WordleScore.id).label('games_played'),
            func.avg(WordleScore.attempts).label('avg_attempts'),
            func.sum(case((WordleScore.solved == True, 1), else_=0)).label('games_won')
        ).filter_by(user_id=current_user.id).first()

        recent_games = session_db.query(WordleScore) \
            .filter_by(user_id=current_user.id) \
            .order_by(WordleScore.date_played.desc()) \
            .limit(10) \
            .all()

    return render_template('wordle_stats.html', stats=stats, recent_games=recent_games)


@app.route('/connections', methods=['GET', 'POST'])
@login_required
def baseball_connections():
    connections = BaseballConnections()

    # Check if game state exists and belongs to current user
    if 'connections_state' in session:
        state = session['connections_state']
        if state.get('user_id') != current_user.id:
            # Different user, clear the state
            session.pop('connections_state')

    # Initialize or load game state
    if 'connections_state' not in session:
        with Session() as session_db:
            puzzle = connections.get_daily_puzzle(session_db)

        session['connections_state'] = {
            'user_id': current_user.id,  # Add user ID
            'puzzle': puzzle,
            'found_groups': [],
            'mistakes': 0,
            'selected': [],
            'start_time': time.time(),
            'game_over': False
        }

    state = session['connections_state']
    print(f"DEBUG: State puzzle items: {state.get('puzzle', {}).get('puzzle_items', [])}")

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'select':
            item = request.form.get('item')
            if item in state['selected']:
                state['selected'].remove(item)
            else:
                if len(state['selected']) < 4:
                    state['selected'].append(item)

        elif action == 'submit':
            if len(state['selected']) == 4:
                is_correct, category, difficulty = connections.check_guess(
                    state['selected'],
                    state['puzzle']
                )

                if is_correct:
                    state['found_groups'].append({
                        'category': category,
                        'items': state['selected'],
                        'difficulty': difficulty,
                        'description': state['puzzle']['categories'][category]['description']
                    })
                    # Remove found items from puzzle
                    for item in state['selected']:
                        state['puzzle']['puzzle_items'].remove(item)
                    state['selected'] = []

                    # Check if game is won
                    if len(state['found_groups']) == 4:
                        state['game_over'] = True
                        time_taken = int(time.time() - state['start_time'])

                        # Save score for won game
                        with Session() as session_db:
                            score = ConnectionsScore(
                                user_id=current_user.id,
                                solved=True,
                                mistakes=state['mistakes'],
                                time_taken=time_taken,
                                game_state=json.dumps(state)
                            )
                            session_db.add(score)
                            session_db.commit()

                        flash(
                            f"Congratulations! You solved it in {time_taken} seconds with {state['mistakes']} mistakes!")
                else:
                    state['mistakes'] += 1
                    state['selected'] = []

                    # Check if game is lost
                    if state['mistakes'] >= connections.max_mistakes:
                        state['game_over'] = True
                        time_taken = int(time.time() - state['start_time'])

                        # Save score for lost game
                        with Session() as session_db:
                            score = ConnectionsScore(
                                user_id=current_user.id,
                                solved=False,  # Lost game
                                mistakes=state['mistakes'],
                                time_taken=time_taken,
                                game_state=json.dumps(state)
                            )
                            session_db.add(score)
                            session_db.commit()

                        flash("Game over! You've made too many mistakes.")

        elif action == 'reset_selection':
            state['selected'] = []

        session['connections_state'] = state

    return render_template('connections.html',
                           state=state,
                           max_mistakes=connections.max_mistakes)


@app.route('/strands', methods=['GET', 'POST'])
@login_required
def baseball_strands():
    strands = BaseballStrands()

    # Check if game state exists and belongs to current user
    if 'strands_state' in session:
        state = session['strands_state']
        if state.get('user_id') != current_user.id:
            session.pop('strands_state')

    # Initialize or load game state
    if 'strands_state' not in session:
        with Session() as session_db:
            puzzle = strands.get_daily_puzzle(session_db)

        session['strands_state'] = {
            'user_id': current_user.id,  # Add user ID
            'puzzle': puzzle,
            'found_words': [],
            'selected_cells': [],
            'start_time': time.time(),
            'game_over': False,
            'hint_level': 0,
            'hints_used': 0,
            'current_hint': None,
            'highlighted_cells': []
        }

    state = session['strands_state']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'select_cell':
            row = int(request.form.get('row'))
            col = int(request.form.get('col'))
            cell = (row, col)

            if cell in state['selected_cells']:
                state['selected_cells'].remove(cell)
            else:
                state['selected_cells'].append(cell)

        elif action == 'check_word':
            if len(state['selected_cells']) >= 2:
                # Extract word from selected cells in order
                selected_word = ''.join([
                    state['puzzle']['grid'][cell[0]][cell[1]]
                    for cell in state['selected_cells']
                ])

                if selected_word in state['puzzle']['words'] and selected_word not in state['found_words']:
                    state['found_words'].append(selected_word)
                    # Clear hint when word is found
                    state['current_hint'] = None
                    state['highlighted_cells'] = []

                    # Check if all words found
                    if len(state['found_words']) == len(state['puzzle']['words']):
                        state['game_over'] = True
                        time_taken = int(time.time() - state['start_time'])

                        # Save score - FIXED: added with statement and fixed indentation
                        with Session() as session_db:
                            score = StrandsScore(
                                user_id=current_user.id,
                                solved=True,  # Successfully found all words
                                words_found=len(state['found_words']),
                                time_taken=time_taken,
                                game_state=json.dumps(state),
                                puzzle_date=datetime.utcnow()
                            )
                            session_db.add(score)
                            session_db.commit()

                        # REMOVED contradictory error message
                        flash(f"Congratulations! You found all words in {time_taken} seconds!")

                state['selected_cells'] = []

        elif action == 'clear_selection':
            state['selected_cells'] = []

        elif action == 'get_hint':
            if not state['game_over'] and len(state['found_words']) < len(state['puzzle']['words']):
                state['hint_level'] += 1
                state['hints_used'] += 1

                hint = strands.get_hint(
                    state['puzzle'],
                    state['found_words'],
                    state['hint_level']
                )

                state['current_hint'] = hint

                # For advanced hints, highlight cells
                if hint and hint['type'] == 'reveal' and 'word' in hint:
                    state['highlighted_cells'] = strands.highlight_hint_cells(
                        state['puzzle'],
                        hint['word']
                    )
                else:
                    state['highlighted_cells'] = []

        session['strands_state'] = state

    return render_template('strands.html', state=state)


@app.route('/clear_connections_session')
def clear_connections_session():
    if 'connections_state' in session:
        session.pop('connections_state')
    return redirect(url_for('baseball_connections'))

@app.route('/clear_strands_session')
def clear_strands_session():
    if 'strands_state' in session:
        session.pop('strands_state')
    return redirect(url_for('baseball_strands'))

@app.route('/clear_crossword_session')
def clear_crossword_session():
    if 'crossword_state' in session:
        session.pop('crossword_state')
    return redirect(url_for('baseball_crossword'))

@app.route('/clear_game_sessions')
def clear_game_sessions():
    # Clear all game states
    game_states = ['strands_state', 'connections_state', 'wordle_state', 'crossword_state', 'trivia_state']
    for state in game_states:
        if state in session:
            session.pop(state)
    flash('All game sessions cleared!')
    return redirect(url_for('index'))

@app.route('/connections/stats')
@login_required
def connections_stats():
    print("Connections stats route called")
    with Session() as session_db:
        # Get overall stats
        games_played = session_db.query(func.count(ConnectionsScore.id)) \
                           .filter_by(user_id=current_user.id) \
                           .scalar() or 0
        print(f"Games played: {games_played}")
        games_won = session_db.query(func.count(ConnectionsScore.id)) \
                        .filter_by(user_id=current_user.id, solved=True) \
                        .scalar() or 0

        avg_mistakes = session_db.query(func.avg(ConnectionsScore.mistakes)) \
                           .filter_by(user_id=current_user.id) \
                           .scalar() or 0

        avg_time = session_db.query(func.avg(ConnectionsScore.time_taken)) \
                       .filter_by(user_id=current_user.id, solved=True) \
                       .scalar() or 0

        best_time = session_db.query(func.min(ConnectionsScore.time_taken)) \
                        .filter_by(user_id=current_user.id, solved=True) \
                        .scalar() or 0

        perfect_games = session_db.query(func.count(ConnectionsScore.id)) \
                            .filter_by(user_id=current_user.id, solved=True, mistakes=0) \
                            .scalar() or 0

        # Get mistake distribution
        mistake_distribution = session_db.query(
            ConnectionsScore.mistakes,
            func.count(ConnectionsScore.id).label('count')
        ).filter_by(user_id=current_user.id) \
            .group_by(ConnectionsScore.mistakes) \
            .order_by(ConnectionsScore.mistakes) \
            .all()

        # Get recent games
        recent_games = session_db.query(ConnectionsScore) \
            .filter_by(user_id=current_user.id) \
            .order_by(ConnectionsScore.puzzle_date.desc()) \
            .limit(10) \
            .all()

        # Calculate streak
        all_games = session_db.query(ConnectionsScore) \
            .filter_by(user_id=current_user.id) \
            .order_by(ConnectionsScore.puzzle_date.desc()) \
            .all()

        current_streak = 0
        best_streak = 0
        temp_streak = 0

        for game in all_games:
            if game.solved:
                temp_streak += 1
                current_streak = temp_streak
                best_streak = max(best_streak, temp_streak)
            else:
                temp_streak = 0

        stats = {
            'games_played': games_played,
            'games_won': games_won,
            'win_rate': (games_won / games_played * 100) if games_played > 0 else 0,
            'avg_mistakes': round(avg_mistakes, 2),
            'avg_time': int(avg_time) if avg_time else 0,
            'best_time': int(best_time) if best_time else 0,
            'perfect_games': perfect_games,
            'current_streak': current_streak,
            'best_streak': best_streak,
            'mistake_distribution': mistake_distribution
        }

        # Detach objects from session
        for game in recent_games:
            session_db.expunge(game)

    return render_template('connections_stats.html', stats=stats, recent_games=recent_games)


@app.route('/strands/stats')
@login_required
def strands_stats():
    with Session() as session_db:
        # Get overall stats
        games_played = session_db.query(func.count(StrandsScore.id)) \
                           .filter_by(user_id=current_user.id) \
                           .scalar() or 0

        games_won = session_db.query(func.count(StrandsScore.id)) \
                        .filter_by(user_id=current_user.id, solved=True) \
                        .scalar() or 0

        total_words_found = session_db.query(func.sum(StrandsScore.words_found)) \
                                .filter_by(user_id=current_user.id) \
                                .scalar() or 0

        avg_words_found = session_db.query(func.avg(StrandsScore.words_found)) \
                              .filter_by(user_id=current_user.id) \
                              .scalar() or 0

        avg_time = session_db.query(func.avg(StrandsScore.time_taken)) \
                       .filter_by(user_id=current_user.id, solved=True) \
                       .scalar() or 0

        best_time = session_db.query(func.min(StrandsScore.time_taken)) \
                        .filter_by(user_id=current_user.id, solved=True) \
                        .scalar() or 0

        # Get word distribution
        word_distribution = session_db.query(
            StrandsScore.words_found,
            func.count(StrandsScore.id).label('count')
        ).filter_by(user_id=current_user.id) \
            .group_by(StrandsScore.words_found) \
            .order_by(StrandsScore.words_found) \
            .all()

        # Get recent games
        recent_games = session_db.query(StrandsScore) \
            .filter_by(user_id=current_user.id) \
            .order_by(StrandsScore.puzzle_date.desc()) \
            .limit(10) \
            .all()

        # Parse game states to get themes
        for game in recent_games:
            if game.game_state:
                try:
                    state = json.loads(game.game_state)
                    game.theme = state.get('puzzle', {}).get('theme', 'Unknown')
                except:
                    game.theme = 'Unknown'
            else:
                game.theme = 'Unknown'

        # Calculate streaks
        all_games = session_db.query(StrandsScore) \
            .filter_by(user_id=current_user.id) \
            .order_by(StrandsScore.puzzle_date.desc()) \
            .all()

        current_streak = 0
        best_streak = 0
        temp_streak = 0

        for game in all_games:
            if game.solved:
                temp_streak += 1
                current_streak = temp_streak
                best_streak = max(best_streak, temp_streak)
            else:
                temp_streak = 0

        stats = {
            'games_played': games_played,
            'games_won': games_won,
            'win_rate': (games_won / games_played * 100) if games_played > 0 else 0,
            'total_words_found': total_words_found,
            'avg_words_found': round(avg_words_found, 2) if avg_words_found else 0,
            'avg_time': int(avg_time) if avg_time else 0,
            'best_time': int(best_time) if best_time else 0,
            'current_streak': current_streak,
            'best_streak': best_streak,
            'word_distribution': word_distribution
        }

        # Detach objects from session
        for game in recent_games:
            session_db.expunge(game)

    return render_template('strands_stats.html', stats=stats, recent_games=recent_games)


from flask import render_template, request, session, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import app, Session
from datetime import datetime
import time, json
from app.baseball_crossword import BaseballCrossword
from app.models import CrosswordPuzzle, CrosswordWordUsage, CrosswordScore, CrosswordHint

from flask import render_template, request, session, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import app, Session
from datetime import datetime
import time, json
from app.baseball_crossword import BaseballCrossword
from app.models import (
    CrosswordPuzzle,
    CrosswordWordUsage,
    CrosswordScore,
    CrosswordHint
)

@app.route('/crossword', methods=['GET', 'POST'])
@login_required
def baseball_crossword():
    crossword = BaseballCrossword()
    today = datetime.utcnow().date()

    # 1) Load or generate today's puzzle
    with Session() as session_db:
        puzzle_record = (
            session_db.query(CrosswordPuzzle)
            .filter(func.date(CrosswordPuzzle.puzzle_date) == today)
            .first()
        )
        if not puzzle_record:
            puzzle_data = crossword.get_daily_puzzle(session_db)
            word_count = (
                len(puzzle_data.get('word_positions', {}).get('across', {})) +
                len(puzzle_data.get('word_positions', {}).get('down', {}))
            )
            total_letters = sum(
                len(info['answer'])
                for d in ('across', 'down')
                for info in puzzle_data.get(f'{d}_clues', {}).values()
            )
            avg_word_length = (total_letters / word_count) if word_count else 0
            puzzle_record = CrosswordPuzzle(
                puzzle_date=today,
                theme=puzzle_data['theme'],
                difficulty=puzzle_data.get('difficulty', 'medium'),
                grid_size=crossword.grid_size,
                grid_data=json.dumps(puzzle_data['grid']),
                clues_data=json.dumps({
                    'across': puzzle_data['across_clues'],
                    'down': puzzle_data['down_clues']
                }),
                word_count=word_count,
                total_letters=total_letters,
                avg_word_length=avg_word_length
            )
            session_db.add(puzzle_record)
            session_db.commit()
            for direction in ('across', 'down'):
                for num, info in puzzle_data[f'{direction}_clues'].items():
                    session_db.add(CrosswordWordUsage(
                        word=info['answer'],
                        puzzle_id=puzzle_record.id,
                        direction=direction,
                        position_row=info['row'],
                        position_col=info['col'],
                        clue=info['clue']
                    ))
            session_db.commit()
        puzzle_data = {
            'grid': json.loads(puzzle_record.grid_data),
            'across_clues': json.loads(puzzle_record.clues_data)['across'],
            'down_clues': json.loads(puzzle_record.clues_data)['down'],
            'theme': puzzle_record.theme,
            'difficulty': puzzle_record.difficulty
        }

    # 2) Reset session if puzzle changed
    if 'crossword_state' in session:
        st = session['crossword_state']
        if st.get('user_id') != current_user.id or st.get('puzzle_id') != puzzle_record.id:
            session.pop('crossword_state')

    # 3) Initialize or load state
    if 'crossword_state' not in session:
        with Session() as session_db:
            existing = session_db.query(CrosswordScore)
            existing = existing.filter_by(user_id=current_user.id,
                                         puzzle_id=puzzle_record.id).first()
        if existing and existing.game_state:
            state = json.loads(existing.game_state)
            state['score_id'] = existing.id
        else:
            user_grid = [['' if c != ' ' else ' ' for c in row]
                         for row in puzzle_data['grid']]
            with Session() as session_db:
                sc = CrosswordScore(
                    user_id=current_user.id,
                    puzzle_id=puzzle_record.id,
                    started_at=datetime.utcnow(),
                    total_cells=puzzle_record.total_letters
                )
                session_db.add(sc)
                session_db.commit()
                session_db.refresh(sc)
                score_id = sc.id
            state = {
                'user_id': current_user.id,
                'puzzle_id': puzzle_record.id,
                'score_id': score_id,
                'puzzle': puzzle_data,
                'user_grid': user_grid,
                'start_time': time.time(),
                'game_over': False,
                'hints_used': 0,
                'current_hint': None,
                'completed_words': {'across': [], 'down': []}
            }
        session['crossword_state'] = state
    state = session['crossword_state']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_cell':
            r = int(request.form.get('row'))
            c = int(request.form.get('col'))
            v = request.form.get('value', '').upper()
            if 0 <= r < crossword.grid_size and 0 <= c < crossword.grid_size:
                if state['puzzle']['grid'][r][c] != ' ':
                    state['user_grid'][r][c] = v[:1]
            session['crossword_state'] = state
            session.modified = True
            return render_template('crossword.html', state=state)

        elif action == 'get_hint':
            state['hints_used'] += 1
            state['current_hint'] = None
            with Session() as session_db:
                hint = crossword.get_hint(
                    session_db,
                    state['puzzle'],
                    state['user_grid'],
                    state['hints_used']
                )
                if hint:
                    state['current_hint'] = hint
                    session_db.add(CrosswordHint(
                        score_id=state['score_id'],
                        hint_type=hint['type'],
                        hint_level=state['hints_used'],
                        hint_content=json.dumps(hint)
                    ))
                    sc = session_db.query(CrosswordScore).get(state['score_id'])
                    sc.hints_used = state['hints_used']
                    session_db.commit()
                    if hint['type'] == 'reveal_letter':
                        row, col = hint['row'], hint['col']
                        state['user_grid'][row][col] = hint['letter']
                        flash(f"Revealed letter: {hint['letter']}")
                    elif hint['type'] == 'reveal_word':
                        r0, c0 = hint['row'], hint['col']
                        for i, ch in enumerate(hint['word']):
                            if hint['direction'] == 'across':
                                state['user_grid'][r0][c0 + i] = ch
                            else:
                                state['user_grid'][r0 + i][c0] = ch
                        state['completed_words'][hint['direction']].append(hint['number'])
                        flash(f"Revealed {hint['direction']} {hint['number']}: {hint['word']}")
                else:
                    flash("No more hints available!")
            session['crossword_state'] = state
            session.modified = True
            return render_template('crossword.html', state=state)

        elif action == 'submit':
            solved = True
            for i, row in enumerate(state['puzzle']['grid']):
                for j, letter in enumerate(row):
                    if letter != ' ' and state['user_grid'][i][j] != letter:
                        solved = False
                        break
                if not solved:
                    break
            if solved:
                state['game_over'] = True
                tt = int(time.time() - state['start_time'])
                state['time_taken'] = tt
                session['crossword_state'] = state
                session.modified = True
                with Session() as session_db:
                    sc = session_db.query(CrosswordScore).get(state['score_id'])
                    sc.solved = True
                    sc.time_taken = tt
                    sc.completed_at = datetime.utcnow()
                    # NEW: set full completion
                    sc.cells_filled = puzzle_record.total_letters
                    sc.completion_percentage = 100.0
                    session_db.commit()
                flash(f"Congratulations! Crossword solved in {tt}s!")
            else:
                flash("Not quite — keep going!")
            return render_template('crossword.html', state=state)

        elif action == 'clear':
            for i in range(len(state['user_grid'])):
                for j in range(len(state['user_grid'][i])):
                    if state['puzzle']['grid'][i][j] != ' ':
                        state['user_grid'][i][j] = ''
            state['hints_used'] = 0
            state['current_hint'] = None
            state['completed_words'] = {'across': [], 'down': []}
            session['crossword_state'] = state
            session.modified = True
            flash("Grid cleared.")
            return render_template('crossword.html', state=state)

        return render_template('crossword.html', state=state)

    return render_template('crossword.html', state=state)






@app.route('/crossword/stats')
@login_required
def crossword_stats():
    with Session() as session_db:
        # Complex query using CTEs and window functions
        stats_query = text("""
        WITH UserStats AS (
            SELECT 
                u.id as user_id,
                COUNT(cs.id) as games_played,
                COUNT(CASE WHEN cs.solved = 1 THEN 1 END) as games_won,
                AVG(CASE WHEN cs.solved = 1 THEN cs.time_taken END) as avg_solve_time,
                MIN(CASE WHEN cs.solved = 1 THEN cs.time_taken END) as best_time,
                AVG(cs.hints_used) as avg_hints,
                AVG(cs.completion_percentage) as avg_completion,
                COUNT(CASE WHEN cs.hints_used = 0 AND cs.solved = 1 THEN 1 END) as perfect_games
            FROM users u
            LEFT JOIN crossword_scores cs ON u.id = cs.user_id
            WHERE u.id = :user_id
            GROUP BY u.id
        ),
        DifficultyStats AS (
            SELECT 
                cp.difficulty,
                COUNT(cs.id) as games_played,
                COUNT(CASE WHEN cs.solved = 1 THEN 1 END) as games_won,
                AVG(CASE WHEN cs.solved = 1 THEN cs.time_taken END) as avg_time
            FROM crossword_puzzles cp
            JOIN crossword_scores cs ON cp.id = cs.puzzle_id
            WHERE cs.user_id = :user_id
            GROUP BY cp.difficulty
        ),
        WordStats AS (
            SELECT 
                cwu.word,
                COUNT(*) as times_encountered,
                SUM(CASE WHEN cs.solved = 1 THEN 1 ELSE 0 END) as times_solved,
                AVG(cwu.difficulty_rating) as difficulty
            FROM crossword_word_usage cwu
            JOIN crossword_puzzles cp ON cwu.puzzle_id = cp.id
            JOIN crossword_scores cs ON cp.id = cs.puzzle_id
            WHERE cs.user_id = :user_id
            GROUP BY cwu.word
            ORDER BY times_encountered DESC
            LIMIT 10
        ),
        RecentGames AS (
            SELECT 
                cs.*,
                cp.theme,
                cp.difficulty,
                cp.word_count,
                RANK() OVER (ORDER BY cs.puzzle_date DESC) as recency_rank
            FROM crossword_scores cs
            JOIN crossword_puzzles cp ON cs.puzzle_id = cp.id
            WHERE cs.user_id = :user_id
        )
        SELECT 
            us.*,
            (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                'difficulty', difficulty,
                'games_played', games_played,
                'games_won', games_won,
                'avg_time', avg_time
            )) FROM DifficultyStats) as difficulty_stats,
            (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                'word', word,
                'times_encountered', times_encountered,
                'times_solved', times_solved,
                'difficulty', difficulty
            )) FROM WordStats) as word_stats,
            (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                'id', id,
                'puzzle_date', puzzle_date,
                'solved', solved,
                'time_taken', time_taken,
                'hints_used', hints_used,
                'completion_percentage', completion_percentage,
                'theme', theme,
                'difficulty', difficulty,
                'word_count', word_count
            )) FROM RecentGames WHERE recency_rank <= 10) as recent_games
        FROM UserStats us
        """)

        result = session_db.execute(stats_query, {"user_id": current_user.id}).fetchone()

        # Performance trend query
        trend_query = text("""
        SELECT 
            DATE(cs.puzzle_date) as date,
            AVG(cs.completion_percentage) as avg_completion,
            AVG(CASE WHEN cs.solved = 1 THEN cs.time_taken END) as avg_time,
            COUNT(*) as games_played
        FROM crossword_scores cs
        WHERE cs.user_id = :user_id
        AND cs.puzzle_date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
        GROUP BY DATE(cs.puzzle_date)
        ORDER BY date
        """)

        trend_data = session_db.execute(trend_query, {"user_id": current_user.id}).fetchall()

        # Parse JSON data
        stats = {
            'games_played': result.games_played or 0,
            'games_won': result.games_won or 0,
            'win_rate': (result.games_won / result.games_played * 100) if result.games_played else 0,
            'avg_solve_time': int(result.avg_solve_time) if result.avg_solve_time else 0,
            'best_time': int(result.best_time) if result.best_time else 0,
            'avg_hints': round(result.avg_hints, 1) if result.avg_hints else 0,
            'avg_completion': round(result.avg_completion, 1) if result.avg_completion else 0,
            'perfect_games': result.perfect_games or 0,
            'difficulty_stats': json.loads(result.difficulty_stats) if result.difficulty_stats else [],
            'word_stats': json.loads(result.word_stats) if result.word_stats else [],
            'recent_games': json.loads(result.recent_games) if result.recent_games else [],
            'trend_data': [{'date': row.date.strftime('%Y-%m-%d'),
                            'avg_completion': float(row.avg_completion),
                            'avg_time': int(row.avg_time) if row.avg_time else 0,
                            'games_played': row.games_played} for row in trend_data]
        }

    return render_template('crossword_stats.html', stats=stats)


@app.route('/crossword/leaderboard')
@login_required
def crossword_leaderboard():
    with Session() as session_db:
        leaderboard_sql = text("""
        WITH UserPerformance AS (
            SELECT 
                u.id,
                u.username,
                SUM(CASE WHEN cs.solved = 1 THEN 1 ELSE 0 END)        AS games_won,
                COUNT(cs.id)                                         AS total_games,
                AVG(cs.hints_used)                                   AS avg_hints,
                SUM(CASE WHEN cs.solved = 1 AND cs.hints_used = 0 THEN 1 ELSE 0 END)
                                                                      AS perfect_games,
                AVG(CASE WHEN cs.solved = 1 THEN cs.time_taken END)   AS avg_solve_time,
                MIN(CASE WHEN cs.solved = 1 THEN cs.time_taken END)   AS best_time,
                100.0 * SUM(CASE WHEN cs.solved = 1 THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(cs.id), 0)                      AS win_rate
            FROM users u
            JOIN crossword_scores cs ON cs.user_id = u.id
            GROUP BY u.id, u.username
            HAVING COUNT(cs.id) >= 1
        ),
        RankedUsers AS (
            SELECT
                *,
                RANK() OVER (ORDER BY win_rate DESC, avg_solve_time ASC)  AS overall_rank,
                RANK() OVER (ORDER BY best_time ASC)                     AS speed_rank,
                RANK() OVER (ORDER BY perfect_games DESC)                AS perfect_rank
            FROM UserPerformance
        )
        SELECT *
          FROM RankedUsers
         ORDER BY overall_rank
         LIMIT 50;
        """)
        leaderboard = session_db.execute(leaderboard_sql).fetchall()

        user_rank_sql = text("""
        WITH UP AS (
            SELECT 
                u.id,
                SUM(CASE WHEN cs.solved = 1 THEN 1 ELSE 0 END)      AS games_won,
                COUNT(cs.id)                                       AS total_games,
                AVG(CASE WHEN cs.solved = 1 THEN cs.time_taken END) AS avg_solve_time,
                100.0 * SUM(CASE WHEN cs.solved = 1 THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(cs.id), 0)                    AS win_rate
            FROM users u
            JOIN crossword_scores cs ON cs.user_id = u.id
            GROUP BY u.id
            HAVING COUNT(cs.id) >= 1
        )
        SELECT COUNT(*) + 1 AS rank
          FROM UP
         WHERE (win_rate > (SELECT win_rate FROM UP WHERE id = :uid))
            OR (win_rate = (SELECT win_rate FROM UP WHERE id = :uid)
                AND avg_solve_time < (SELECT avg_solve_time FROM UP WHERE id = :uid));
        """)
        user_rank = session_db.execute(user_rank_sql, {"uid": current_user.id}).scalar()

    return render_template(
        'crossword_leaderboard.html',
        leaderboard=leaderboard,
        user_rank=user_rank
    )
