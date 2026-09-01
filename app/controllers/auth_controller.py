from flask import Blueprint, render, template, request, flash, redirect, url_for
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route("/login")
def login():
    return render_template('login/login.html')

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        confirma_senha = request.form.get('confirma_senha')

        try:
            success, message = auth_service.register_user(nome, email, senha, confirma_senha)
            if success:
                flash(message, 'success')
                return redirect(url_for('auth.login'))
        except ValueError as ve:
            flash(str(ve), 'error')
        except Exception as e:
            flash(str(e), 'error')

    return render_template('login/register.html', site='tcc-vm-megha.onrender.com')