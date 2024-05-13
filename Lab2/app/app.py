from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    url = request.url
    title = "Лр 2"
    return render_template("index.html", title=title, url=url)

@app.route('/request_data')
def request_data():
    return render_template('request_data.html',
                           url_params=request.args,
                           headers=request.headers,
                           cookies=request.cookies,
                           form_data=request.form)

@app.route('/phone', methods=['GET', 'POST'])
def phone():
    error = None
    formatted_number = None
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '')
        error = validate_phone_number(phone_number)
        if not error:
            formatted_number = format_phone_number(phone_number)
    return render_template('phone_form.html', error=error, formatted_number=formatted_number)

def validate_phone_number(phone_number):
    cleaned_number = ''.join(filter(str.isdigit, phone_number))
    if not cleaned_number:
        return "Введите номер телефона"
    elif len(cleaned_number) == 10:
        return None
    elif len(cleaned_number) == 11 and cleaned_number.startswith(('7', '8')):
        return None
    elif not phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '').isdigit():
        return "Недопустимый ввод. В номере телефона встречаются недопустимые символы."
    else:
        return "Недопустимый ввод. Неверное количество цифр"
    

def format_phone_number(phone_number):
    cleaned_number = ''.join(filter(str.isdigit, phone_number))
    if len(cleaned_number) == 11:
        cleaned_number = cleaned_number[1:]
    formatted_number = f'8-{cleaned_number[:3]}-{cleaned_number[3:6]}-{cleaned_number[6:8]}-{cleaned_number[8:]}'

    
    return formatted_number


if __name__ == '__main__':
    app.run(debug=True)