import os
from urllib.parse import urlencode

from flask import Flask, render_template, request, jsonify, redirect
from requests import post

app = Flask(__name__)


@app.route('/')
def main():
    return render_template('main.html', title="Добро пожаловать!")


@app.route('/login')
def login():
    if request.cookies.get("name"):
        return redirect("/account")
    code = request.args.get("code")
    if code:
        token = post("https://oauth.yandex.ru/token", urlencode({
            'grant_type': 'authorization_code',
            'code': request.args.get('code'),
            'client_id': "5e6a0be5bbfe4606be5c35a28e6fe741",
            'client_secret': "003775f9aa174049badefcaf785f9dde"
        })).json().get("access_token")
        if token:
            accinfo = post(f"https://login.yandex.ru/info?oauth_token={token}")
            accinfo.encoding = "utf-8"
            accinfo = accinfo.json()
            resp = app.make_response(render_template("process.html", title="Авторизация...", redirect="/account"))
            resp.set_cookie('name', f'{accinfo.get("first_name")} {accinfo.get("last_name")}', max_age=2592000)
            return resp
        return redirect("https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")
    return redirect("https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")


@app.route('/account')
def account():
    if request.cookies.get("name"):
        return render_template('account.html', title="Личный кабинет", user=request.cookies.get("name"))
    else:
        return redirect('/login')


@app.route('/quit')
def quit():
    if request.cookies.get("name"):
        resp = app.make_response(render_template("main.html", title="Добро пожаловать!"))
        resp.set_cookie('name', "None", max_age=0)
        return resp
    else:
        return redirect('/login')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
