from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required
# from .controllers import register_user, verify_credentials

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # credentials = verify_credentials(request.form['email'], request.form['password'])
        # if credentials are valid:
        #     login_user(user_object)
        #     return redirect(url_for('main_bp.index'))
        pass
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # register_user(request.form['email'], request.form['password'])
        return redirect(url_for('auth_bp.login'))
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))
