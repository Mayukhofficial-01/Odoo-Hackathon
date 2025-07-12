from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Answer, Question, Upvote
from app.forms import RegisterForm, LoginForm, RequestResetForm, ResetPasswordForm, AskQuestionForm, AnswerForm
from app import db, bcrypt, mail
from flask_mail import Message
from sqlalchemy.exc import IntegrityError
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Password Reset Request",
                  sender="stackitteam@gmail.com",
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg)

def register_routes(app):
    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        return redirect(url_for("login"))

    @app.route("/index")
    @login_required
    def index():
        questions = Question.query.order_by(Question.date_posted.desc()).all()
        return render_template("index.html", questions=questions)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            existing_user = User.query.filter_by(username=form.username.data).first()
            existing_email = User.query.filter_by(email=form.email.data).first()

            if existing_user:
                flash("Username already taken. Please choose another one.", "danger")
                return render_template("register.html", form=form)

            if existing_email:
                flash("Email already registered. Try logging in instead.", "danger")
                return render_template("register.html", form=form)

            try:
                hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
                db.session.add(user)
                db.session.commit()

                msg = Message("Team StackIt - Welcome to Our Website! Meet New People and Answer to their doubts",
                              sender="stackitteam@gmail.com",
                              recipients=[form.email.data])
                msg.body = f"Hi {form.username.data},\n\nThanks for joining StackIt!"
                mail.send(msg)

                login_user(user)  # ✅ Log in user after registration
                flash("Account created successfully. Welcome to StackIt!", "success")
                return redirect(url_for("index"))  # ✅ Redirect to index

            except IntegrityError:
                db.session.rollback()
                flash("An error occurred while creating the account. Please try again.", "danger")

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                flash("Logged in successfully.", "success")
                return redirect(url_for("index"))
            flash("Invalid credentials", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/reset_password", methods=["GET", "POST"])
    def reset_request():
        form = RequestResetForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                send_reset_email(user)
                flash("An email has been sent with instructions to reset your password.", "info")
                return redirect(url_for('login'))
            else:
                flash("No account found with that email.", "danger")
        return render_template("reset_request.html", form=form)

    @app.route("/reset_password/<token>", methods=["GET", "POST"])
    def reset_token(token):
        user = User.verify_reset_token(token)
        if user is None:
            flash("That is an invalid or expired token.", "warning")
            return redirect(url_for("reset_request"))

        form = ResetPasswordForm()
        if form.validate_on_submit():
            hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.password = hashed_pw
            db.session.commit()
            flash("Your password has been updated! You can now log in.", "success")
            return redirect(url_for("login"))
        return render_template("reset_token.html", form=form)

    @app.route("/ask", methods=["GET", "POST"])
    @login_required
    def ask_question():
        form = AskQuestionForm()
        if form.validate_on_submit():
            question = Question(
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                user_id=current_user.id
            )
            db.session.add(question)
            db.session.commit()
            flash("Question posted successfully!", "success")
            return redirect(url_for("index"))
        return render_template("ask_question.html", form=form)

    @app.route("/question/<int:question_id>", methods=["GET", "POST"])
    def view_question(question_id):
        question = Question.query.get_or_404(question_id)
        form = AnswerForm()

        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash("You must be logged in to answer.", "danger")
                return redirect(url_for("login"))
            answer = Answer(content=form.content.data, question_id=question.id, user_id=current_user.id)
            db.session.add(answer)
            db.session.commit()
            flash("Your answer has been posted!", "success")
            return redirect(url_for("view_question", question_id=question.id))

        answers = Answer.query.filter_by(question_id=question.id).order_by(Answer.date_posted.desc()).all()
        return render_template("view_question.html", question=question, form=form, answers=answers)

    @app.route("/dashboard")
    @login_required
    def dashboard():
        total_upvotes = sum(answer.upvotes for answer in current_user.answers)
        user_questions = Question.query.filter_by(user_id=current_user.id).order_by(Question.date_posted.desc()).all()
        return render_template("dashboard.html", questions=user_questions, total_upvotes=total_upvotes, answers=current_user.answers)

    @app.route('/upload_profile_pic', methods=['POST'])
    @login_required
    def upload_profile_pic():
        if 'profile_pic' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('dashboard'))

        file = request.files['profile_pic']

        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('dashboard'))

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.root_path, 'static/profile_pics', filename)
            file.save(file_path)

            current_user.profile_pic = f'profile_pics/{filename}'
            current_user.updated_at = datetime.utcnow()
            db.session.commit()

            flash('Profile picture updated successfully!', 'success')
            return redirect(url_for('dashboard'))

    @app.route('/search_users')
    def search_users():
        query = request.args.get('q', '')
        if not query:
            flash("Please enter a search query.", "warning")
            return redirect(url_for('index'))

        results = User.query.filter(User.username.ilike(f"%{query}%")).all()
        return render_template("search_results.html", query=query, results=results)

    @app.route('/user/<username>')
    def view_user_profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        questions = user.questions
        answers = user.answers
        return render_template('user_profile.html', user=user, questions=questions, answers=answers)

    @app.route('/upvote_answer/<int:answer_id>', methods=['POST'])
    @login_required
    def upvote_answer(answer_id):
        answer = Answer.query.get_or_404(answer_id)
        existing_upvote = Upvote.query.filter_by(user_id=current_user.id, answer_id=answer_id).first()
        if existing_upvote:
            flash("You already upvoted this answer.", "info")
            return redirect(request.referrer or url_for('index'))

        new_upvote = Upvote(user_id=current_user.id, answer_id=answer_id)
        db.session.add(new_upvote)
        answer.upvotes += 1
        db.session.commit()

        flash("Upvoted successfully!", "success")
        return redirect(request.referrer or url_for('index'))
