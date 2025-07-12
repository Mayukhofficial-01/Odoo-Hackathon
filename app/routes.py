from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models import User
from app.forms import RegisterForm, LoginForm, RequestResetForm, ResetPasswordForm
from app import db, bcrypt, mail
from flask_mail import Message
from sqlalchemy.exc import IntegrityError
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Password Reset Request",
                  sender="rounakchakraborti499@gmail.com",
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg)

def register_routes(app):
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

                msg = Message("Welcome to StackIt!",
                              sender="your_email@gmail.com",
                              recipients=[form.email.data])
                msg.body = f"Hi {form.username.data},\n\nThanks for joining StackIt!"
                mail.send(msg)

                flash("Account created successfully and welcome email sent.", "success")
                return redirect(url_for("login"))

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

    @app.route("/")
    def index():
        return render_template("index.html")

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

    