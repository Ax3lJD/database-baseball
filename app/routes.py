from flask import render_template, flash, redirect, url_for, request, session
from app import app, engine, Session
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.forms import LoginForm, RegisterForm
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User, TriviaScore
import random
from flask_login import login_user, logout_user, current_user, login_required
from app.trivia_questions import generate_player_stat_question, generate_team_performance_question
import traceback


@app.route('/')
@app.route('/index')
def index():
    user = current_user if current_user.is_authenticated else None

    welcome_message = "Welcome to Triviamania! Test your baseball knowledge and climb the leaderboard."

    return render_template(
        'index.html',
        title='Home',
        user=user,
        welcome_message=welcome_message
    )

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied: Admins only.")
        return redirect(url_for('index'))
    
    with Session() as session_db:
        users = session_db.query(User).all()
    
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/toggle_ban/<int:user_id>', methods=['POST'])
@login_required
def toggle_ban(user_id):
    if not current_user.is_admin:
        flash("Access denied.")
        return redirect(url_for('index'))

    session_db = Session()
    user = session_db.query(User).filter_by(id=user_id).first()
    if user:
        user.is_banned = not user.is_banned
        session_db.commit()
        flash(f"User {user.username} ban status updated.")
    else:
        flash("User not found.")
    session_db.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session_db = Session()
        user = session_db.query(User).filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if user.is_banned:
                flash("This user is banned.")
                session_db.close()
                return redirect(url_for('login'))
            else:
                login_user(user)
                flash(f'Welcome, {user.username}!')
                session_db.close()
                if user.is_admin:
                    return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
            session_db.close()
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
        session_db = Session()
        hashed_pw = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password_hash=hashed_pw, is_admin=False, is_banned=False)
        session_db.add(new_user)
        session_db.commit()
        session_db.close()
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

            latest_score = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(TriviaScore.round_number.desc()).first()
            session['round_number'] = (latest_score.round_number + 1) if latest_score else 1

            if session['question_count'] >= 10:
                correct_answers = session['correct_answers']
                score = session['score']
                round_number = session['round_number']

                new_score = TriviaScore(
                    user_id=current_user.id,
                    score=score,
                    total_attempted=10,
                    correct_answers=correct_answers,
                    percentage=round((correct_answers / 10) * 100, 2),
                    round_number=round_number
                )
                session_db.add(new_score)
                session_db.commit()

                session['question_count'] = 0
                session['score'] = 0
                session['correct_answers'] = 0
                session['round_number'] += 1

                return redirect(url_for('trivia_results'))

            generator = random.choice([generate_player_stat_question, generate_team_performance_question])
            question_data = generator(session_db)

            if not question_data:
                flash("Not enough data to generate a trivia question. Try again.")
                return redirect(url_for('trivia'))

            if request.method == 'POST':
                user_answer = request.form.get('answer')
                if user_answer == question_data['correct_letter']:
                    flash("Correct! 🎉")
                    session['score'] += 1
                    session['correct_answers'] += 1
                else:
                    correct_answer_text = question_data['options'].get(question_data['correct_letter'])
                    flash(f"Wrong. The correct answer was {question_data['correct_letter']}) {correct_answer_text}")
                session['question_count'] += 1
                return redirect(url_for('trivia'))

            return render_template(
                'trivia.html',
                question=question_data['question'],
                options=question_data['options'],
                question_number=session['question_count'] + 1
            )

    except Exception as e:
        print("An error occurred:")
        traceback.print_exc()
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('index'))

@app.route('/trivia/results')
def trivia_results():
    session_db = Session()

    # Get the latest score for the user
    latest_score = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(TriviaScore.round_number.desc()).first()

    if latest_score:
        score = latest_score.score
        total_attempted = latest_score.total_attempted
        correct_answers = latest_score.correct_answers
        percentage = latest_score.percentage
        round_number = latest_score.round_number
    else:
        score = total_attempted = correct_answers = percentage = round_number = 0

    # Get top 10 rounds
    rounds = session_db.query(TriviaScore).filter_by(user_id=current_user.id).order_by(TriviaScore.score.desc()).limit(10).all()

    session_db.close()

    return render_template(
        'results.html',
        title='Your Trivia Results',
        latest_score=latest_score,
        rounds=rounds
    )