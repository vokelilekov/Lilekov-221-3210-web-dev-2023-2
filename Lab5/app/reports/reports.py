from app import app
from flask import Blueprint, render_template, send_file, request
from app import db_connector
import csv
import io
from app.decorators import check_rights
from flask_login import login_required, current_user

reports_bp = Blueprint('reports', __name__, template_folder='templates')

@reports_bp.route('/visit_logs')
@login_required
@check_rights('view_visit_log')
def visit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    if current_user.role_name == 'Admin':
        query = """
        SELECT visit_logs.id, visit_logs.path, visit_logs.created_at, users.login 
        FROM visit_logs 
        LEFT JOIN users ON visit_logs.user_id = users.id 
        ORDER BY visit_logs.created_at DESC 
        LIMIT %s OFFSET %s
        """
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (per_page, (page - 1) * per_page))
            logs = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS total FROM visit_logs")
            total = cursor.fetchone().total
    else:
        query = """
        SELECT visit_logs.id, visit_logs.path, visit_logs.created_at, users.login 
        FROM visit_logs 
        LEFT JOIN users ON visit_logs.user_id = users.id 
        WHERE visit_logs.user_id = %s
        ORDER BY visit_logs.created_at DESC 
        LIMIT %s OFFSET %s
        """
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (current_user.id, per_page, (page - 1) * per_page))
            logs = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS total FROM visit_logs WHERE user_id = %s", (current_user.id,))
            total = cursor.fetchone().total

    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_next': page * per_page < total,
        'has_prev': page > 1,
        'next_num': page + 1,
        'prev_num': page - 1
    }

    return render_template('visit_logs.html', logs=logs, pagination=pagination)

@reports_bp.route('/report/pages')
@login_required
@check_rights('view_visit_log')
def report_pages():
    query = "SELECT path, COUNT(*) as visit_count FROM visit_logs GROUP BY path ORDER BY visit_count DESC"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        page_stats = cursor.fetchall()

    return render_template('report_pages.html', page_stats=page_stats)

@reports_bp.route('/report/pages/export')
@login_required
@check_rights('view_visit_log')
def export_pages():
    query = "SELECT path, COUNT(*) as visit_count FROM visit_logs GROUP BY path ORDER BY visit_count DESC"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        page_stats = cursor.fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Page', 'Visit Count'])
    for row in page_stats:
        cw.writerow([row.path, row.visit_count])

    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)

    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='page_report.csv')

@reports_bp.route('/report/users')
@login_required
@check_rights('view_visit_log')
def report_users():
    query = "SELECT users.login, COUNT(*) as visit_count FROM visit_logs LEFT JOIN users ON visit_logs.user_id = users.id GROUP BY users.login ORDER BY visit_count DESC"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        user_stats = cursor.fetchall()

    return render_template('report_users.html', user_stats=user_stats)

@reports_bp.route('/report/users/export')
@login_required
@check_rights('view_visit_log')
def export_users():
    query = "SELECT users.login, COUNT(*) as visit_count FROM visit_logs LEFT JOIN users ON visit_logs.user_id = users.id GROUP BY users.login ORDER BY visit_count DESC"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        user_stats = cursor.fetchall()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['User', 'Visit Count'])
    for row in user_stats:
        cw.writerow([row.login or 'Unauthenticated User', row.visit_count])

    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)

    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='user_report.csv')
