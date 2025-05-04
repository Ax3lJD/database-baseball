from flask import render_template, flash, redirect, url_for, request, session
from app import app, engine, Session
from sqlalchemy import text, func, case
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.forms import LoginForm, RegisterForm
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User, TriviaScore
import random
from flask_login import login_user, logout_user, current_user, login_required
from app.trivia_questions import generate_player_stat_question, generate_team_performance_question
import traceback
from app.baseball_wordle import BaseballWordle
from app.models import WordleScore
from datetime import datetime, date
import json
from app.baseball_connections import BaseballConnections
from app.models import ConnectionsScore
import time
from app.baseball_strands import BaseballStrands
from app.models import StrandsScore


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
        }
    ]

    user_stats = None
    if current_user.is_authenticated:
        with Session() as session_db:
            trivia_count = session_db.query(TriviaScore).filter_by(user_id=current_user.id).count()
            wordle_count = session_db.query(WordleScore).filter_by(user_id=current_user.id).count()
            connections_count = session_db.query(ConnectionsScore).filter_by(user_id=current_user.id).count()
            strands_count = session_db.query(StrandsScore).filter_by(user_id=current_user.id).count()

            user_stats = {
                'trivia_rounds': trivia_count,
                'wordle_games': wordle_count,
                'connections_games': connections_count,
                'strands_games': strands_count
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

    # Initialize or load game state
    if 'connections_state' not in session:
        with Session() as session_db:
            puzzle = connections.get_daily_puzzle(session_db)
            print(f"DEBUG: Generated puzzle: {puzzle}")

        session['connections_state'] = {
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

                        # Save score
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

                    if state['mistakes'] >= connections.max_mistakes:
                        state['game_over'] = True
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

    # Initialize or load game state
    if 'strands_state' not in session:
        with Session() as session_db:
            puzzle = strands.get_daily_puzzle(session_db)

        session['strands_state'] = {
            'puzzle': puzzle,
            'found_words': [],
            'selected_cells': [],
            'start_time': time.time(),
            'game_over': False
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
                # Extract word from selected cells
                selected_word = ''.join([
                    state['puzzle']['grid'][cell[0]][cell[1]]
                    for cell in state['selected_cells']
                ])

                if selected_word in state['puzzle']['words'] and selected_word not in state['found_words']:
                    state['found_words'].append(selected_word)

                    # Check if all words found
                    if len(state['found_words']) == len(state['puzzle']['words']):
                        state['game_over'] = True
                        time_taken = int(time.time() - state['start_time'])

                        # Save score
                        with Session() as session_db:
                            score = StrandsScore(
                                user_id=current_user.id,
                                solved=True,
                                words_found=len(state['found_words']),
                                time_taken=time_taken,
                                game_state=json.dumps(state)
                            )
                            session_db.add(score)
                            session_db.commit()

                        flash(f"Congratulations! You found all words in {time_taken} seconds!")

                state['selected_cells'] = []

        elif action == 'clear_selection':
            state['selected_cells'] = []

        session['strands_state'] = state

    return render_template('strands.html', state=state)


@app.route('/clear_connections_session')
def clear_connections_session():
    if 'connections_state' in session:
        session.pop('connections_state')
    return redirect(url_for('baseball_connections'))


@app.route('/connections/stats')
@login_required
def connections_stats():
    with Session() as session_db:
        # Get overall stats
        games_played = session_db.query(func.count(ConnectionsScore.id)) \
                           .filter_by(user_id=current_user.id) \
                           .scalar() or 0

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