import os
from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def main():
    return render_template('main.html', title="Добро пожаловать!")


@app.route('/account')
def index():
    return render_template('account.html', title="Аккаунт")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
