from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from app.__init__ import *
from mysql.connector.errors import DatabaseError
from werkzeug.security import check_password_hash, generate_password_hash
import re
import hashlib
from functools import wraps
from app.reports.reports import reports_bp
from app.decorators import check_rights

app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')
app.register_blueprint(reports_bp, url_prefix='/reports')
db_connector = DBConnector(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message = "Войдите, чтобы просматривать содержимое данной страницы"
login_manager.login_message_category = "warning"

class User(UserMixin):
    def __init__(self, user_id, login, role_id, role_name, password_hash=None):
        self.id = user_id
        self.login = login
        self.password_hash = password_hash
        self.role_id = role_id
        self.role_name = role_name

def get_roles():
    query = "SELECT id, name FROM roles"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        roles = cursor.fetchall()
    return roles

@app.before_request
def log_visit():
    if request.endpoint not in ('static', 'login', 'logout'):
        user_id = current_user.id if current_user.is_authenticated else None
        query = "INSERT INTO visit_logs (path, user_id) VALUES (%s, %s)"
        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, (request.path, user_id))
                db_connector.connect().commit()
                cursor.fetchall()
        except DatabaseError as error:
            print(f"Error logging visit: {error}")


@login_manager.user_loader
def load_user(user_id):
    query = "SELECT users.id, users.login, users.password_hash, roles.id as role_id, roles.name as role_name FROM users JOIN roles ON users.role_id = roles.id WHERE users.id = %s"
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_id=user_data.id, login=user_data.login, role_id=user_data.role_id, role_name=user_data.role_name, password_hash=user_data.password_hash)
            else:
                print("No user found with ID:", user_id)
    except Exception as e:
        print("Database error:", e) 
    return None

@app.route('/login', methods=["GET", "POST"])
def auth():
    if request.method == "GET":
        return render_template("login.html")
    
    login = request.form.get("username", "")
    password = request.form.get("password", "")
    remember = request.form.get("remember_me") == "on"

    query = 'SELECT id, login, password_hash, role_id, (SELECT name FROM roles WHERE id=role_id) as role_name FROM users WHERE login=%s AND password_hash=SHA2(%s, 256)'
    
    print(query)

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (login, password))
        user = cursor.fetchone()

    if user:
        user_obj = User(user_id=user.id, login=user.login, role_id=user.role_id, role_name=user.role_name, password_hash=user.password_hash)
        login_user(user_obj, remember=remember)
        flash("Успешная авторизация", category="success")
        target_page = request.args.get("next", url_for("index"))
        return redirect(target_page)

    flash("Введены некорректные учётные данные пользователя", category="danger")    

    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    query = """
    SELECT users.id, users.login, users.first_name, users.last_name, users.middle_name, roles.name as role_name
    FROM users
    JOIN roles ON users.role_id = roles.id
    WHERE users.id = %s
    """
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (current_user.id,))
        user = cursor.fetchone()
    
    if user:
        return render_template('profile.html', user=user)
    else:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('index'))

@login_required
@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_own_profile():
    user_id = current_user.id

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        middle_name = request.form.get('middle_name')
        login = request.form.get('login')

        query = """
        UPDATE users
        SET first_name = %s, last_name = %s, middle_name = %s, login = %s
        WHERE id = %s
        """
        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, (first_name, last_name, middle_name, login, user_id))
                db_connector.connect().commit()
                flash('Ваш профиль был успешно обновлен', 'success')
                return redirect(url_for('profile'))
        except DatabaseError as error:
            flash(f'Ошибка обновления профиля! {error}', 'danger')
            db_connector.connect().rollback()

    query = "SELECT id, login, first_name, last_name, middle_name FROM users WHERE id = %s"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

    return render_template('edit_profile.html', user=user)

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

@app.route('/users')
def users():
    query = 'SELECT users.*, roles.name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.id'

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        data = cursor.fetchall() 

    return render_template("users.html", users=data)

def get_form_data(required_fields):
    user = {}

    for field in required_fields:
        user[field] = request.form.get(field) or None

    return user

@app.route('/user/<int:user_id>/show')
@check_rights('view_user')
def show_user(user_id):
    query = 'SELECT users.*, roles.name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.id WHERE users.id = %s'

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone() 

    if user:
        return render_template("show_user.html", user=user)
    else:
        flash('Пользователь с указанным идентификатором не найден', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@check_rights('edit_user')
def edit_user(user_id):
    query = ("SELECT * FROM users where id = %s")
    roles = get_roles()
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone()

    if request.method == "POST":
        user = get_form_data(EDIT_USER_FIELDS)
        user['user_id'] = user_id
        query = ("UPDATE users "
                 "SET last_name=%(last_name)s, first_name=%(first_name)s, "
                 "middle_name=%(middle_name)s, role_id=%(role_id)s "
                 "WHERE id=%(user_id)s ")

        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, user)
                db_connector.connect().commit()
            
            flash("Запись пользователя успешно обновлена", category="success")
            return redirect(url_for('users'))
        except DatabaseError as error:
            flash(f'Ошибка редактирования пользователя! {error}', category="danger")
            db_connector.connect().rollback()    

    return render_template("edit_user.html", user=user, roles=roles)

@app.route('/user/<int:user_id>/delete', methods=["POST"])
@login_required
@check_rights('delete_user')
def delete_user(user_id):
    query = "DELETE FROM users WHERE id=%s"

    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, ))
            db_connector.connect().commit() 
        
        flash("Запись пользователя успешно удалена", category="success")
    except DatabaseError as error:
        flash(f'Ошибка удаления пользователя! {error}', category="danger")
        db_connector.connect().rollback()    
    
    return redirect(url_for('users'))

@app.route('/users/new', methods=['GET', 'POST'])
@login_required
@check_rights('create_user')
def create_user():
    user = {}
    roles = get_roles()
    errors = {}

    if request.method == 'POST':
        user = get_form_data(CREATE_USER_FIELDS)

        if not user['login']:
            errors['login'] = 'Логин не может быть пустым'
        elif not re.match(r'^[a-zA-Z0-9]{5,}$', user['login']):
            errors['login'] = 'Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов'

        if not user['password']:
            errors['password'] = 'Пароль не может быть пустым'
        elif len(user['password']) < 8 or len(user['password']) > 128:
            errors['password'] = 'Пароль должен содержать от 8 до 128 символов'
        elif not (re.search(r'[A-Z]', user['password']) and re.search(r'[a-z]', user['password'])) and not (re.search(r'[А-Я]', user['password']) and re.search(r'[а-я]', user['password'])):
            errors['password'] = 'Пароль должен содержать как минимум одну заглавную и одну строчную букву латиницы или кириллицы'
        elif not re.search(r'\d', user['password']):
            errors['password'] = 'Пароль должен содержать как минимум одну цифру'
        elif ' ' in user['password']:
            errors['password'] = 'Пароль не должен содержать пробелы'
        elif not re.match(r'^[A-Za-zА-Яа-я0-9~!@#$%^&*_\-+()\[\]{}><\\|"\'.,:;]*$', user['password']):
            errors['password'] = 'Пароль должен содержать только латинские или кириллические буквы, цифры и разрешенные символы: ~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " \' . , : ;'

        if not user['last_name']:
            errors['last_name'] = 'Фамилия не может быть пустой'

        if not user['first_name']:
            errors['first_name'] = 'Имя не может быть пустым'

        if not errors:
            user['password'] = generate_password_hash(user['password'])

            query = ("INSERT INTO users "
                    "(login, password_hash, last_name, first_name, middle_name, role_id) "
                    "VALUES (%(login)s, SHA2(%(password)s, 256), "
                    "%(last_name)s, %(first_name)s, %(middle_name)s, %(role_id)s)")
            try:
                with db_connector.connect().cursor(named_tuple=True) as cursor:
                    cursor.execute(query, user)
                    db_connector.connect().commit()
                return redirect(url_for('users'))
            except DatabaseError as error:
                flash(f'Ошибка создания пользователя! {error}', category="danger")    
                db_connector.connect().rollback()

    return render_template("user_form.html", user=user, roles=roles, errors=errors) 

@app.route('/views_count')
def views_count():
    session['visit_count'] = session.get('visit_count', 0) + 1
    return render_template('views_count.html', visit_count=session['visit_count'])

@app.route('/change', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        hashed_old_password = hashlib.sha256(old_password.encode()).hexdigest()
        
        if current_user.password_hash != hashed_old_password:
            errors['old_password'] = 'Неверный старый пароль'

        if new_password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'

        if not new_password:
            errors['new_password'] = 'Пароль не может быть пустым'
        elif len(new_password) < 8 or len(new_password) > 128:
            errors['new_password'] = 'Пароль должен содержать от 8 до 128 символов'
        elif not (re.search(r'[A-Z]', new_password) and re.search(r'[a-z]', new_password)) and not (re.search(r'[А-Я]', new_password) and re.search(r'[а-я]', new_password)):
            errors['new_password'] = 'Пароль должен содержать как минимум одну заглавную и одну строчную букву латиницы или кириллицы'
        elif not re.search(r'\d', new_password):
            errors['new_password'] = 'Пароль должен содержать как минимум одну цифру'
        elif ' ' in new_password:
            errors['new_password'] = 'Пароль не должен содержать пробелы'
        elif not re.match(r'^[A-Za-zА-Яа-я0-9~!@#$%^&*_\-+()\[\]{}><\\|"\'.,:;]*$', new_password):
            errors['new_password'] = 'Пароль должен содержать только латинские или кириллические буквы, цифры и разрешенные символы: ~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " \' . , : ;'

        if not errors:
            new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            query = "UPDATE users SET password_hash = %s WHERE id = %s"
            try:
                with db_connector.connect().cursor(named_tuple=True) as cursor:
                    cursor.execute(query, (new_password_hash, current_user.id))
                    db_connector.connect().commit()
                flash("Пароль успешно изменен", category="success")
                return redirect(url_for('index'))
            except DatabaseError as error:
                flash(f'Ошибка изменения пароля! {error}', category="danger")
                db_connector.connect().rollback()

    return render_template("change.html", errors=errors)

if __name__ == '__main__':
    app.run(debug=True)
