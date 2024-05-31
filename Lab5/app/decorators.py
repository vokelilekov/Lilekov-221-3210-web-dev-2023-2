from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def check_rights(action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = current_user.role_name
            allowed_actions = {
                'Admin': ['create_user', 'edit_user', 'view_user', 'delete_user', 'view_visit_log'],
                'User': ['edit_own_data', 'view_own_profile', 'view_own_visits', 'view_visit_log']
            }
            if action in allowed_actions.get(user_role, []):
                return f(*args, **kwargs)
            else:
                flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
                return redirect(url_for('index'))
        return decorated_function
    return decorator
