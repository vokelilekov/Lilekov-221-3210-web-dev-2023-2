from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

users = {'user': {'password': 'qwerty'}}

class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        user = User()
        user.id = user_id
        return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User()
            user.id = username
            login_user(user)
            session['logged_in'] = True
            flash('Вы успешно вошли', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

@app.route('/views_count')
def views_count():
    session['visit_count'] = session.get('visit_count', 0) + 1
    return render_template('views_count.html', visit_count=session['visit_count'])

if __name__ == '__main__':
    app.run(debug=True)
