from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from job_app_tracker.models.user import User
from job_app_tracker.auth.forms import LoginForm, RegistrationForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.dashboard'))
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.get_by_email(form.email.data):
            flash('Email already registered', 'error')
            return render_template('auth/register.html', form=form)
        
        user = User.create_user(
            email=form.email.data,
            password=form.password.data,
            name=form.name.data
        )
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index')) 