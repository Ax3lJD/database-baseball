from flask import render_template, flash, redirect, url_for
from app import app, engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.forms import LoginForm, RegisterForm
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User
from app import Session

@app.route('/')
@app.route('/index')
def index():
    user = {'username': 'Miguel'}
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]

    # Test database connection
    db_status = "Unknown"
    sample_people = []
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # Basic connection test
            db_status = "✅ Connected to database!"

            # Query the 'people' table for testing
            result = conn.execute(text("SELECT playerID, nameFirst, nameLast FROM people LIMIT 5"))
            sample_people = result.mappings().all()  # returns a list of dict-like row objects

    except OperationalError as e:
        db_status = f"❌ Operational error: {e}"
    except SQLAlchemyError as e:
        db_status = f"❌ Database connection failed: {e}"

    return render_template(
        'index.html',
        title='Home',
        user=user,
        posts=posts,
        db_status=db_status,
        sample_people=sample_people
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = Session()
        user = session.query(User).filter_by(username=form.username.data).first()
        print("Submitted Username:", form.username.data)
        print("User from DB:", user)
        if user:
            print("Stored Hash:", user.password_hash)
            print("Entered Password:", form.password.data)
            print("Password Match:", check_password_hash(user.password_hash, form.password.data))

        if user and check_password_hash(user.password_hash, form.password.data):
            if user.is_banned:
                flash("This user is banned.")
            else:
                flash(f'Welcome, {user.username}!')
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session = Session()
        hashed_pw = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password_hash=hashed_pw, is_admin=False, is_banned=False)
        session.add(new_user)
        session.commit()
        session.close()
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)