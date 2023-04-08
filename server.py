import os
import sqlite3
from urllib.parse import urlencode

import flask
from flask import Flask, render_template, request, jsonify, redirect
from requests import post

app = Flask(__name__)
con = sqlite3.connect("database.db", check_same_thread=False)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        login TEXT, yandex_id TEXT, acctype INTEGER DEFAULT (0), first_name TEXT, last_name TEXT);""")
cur.execute("""CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        teacher_id INTEGER, litter TEXT);""")
cur.execute("""CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        account_id INTEGER, class_id INTEGER, type INTEGER DEFAULT 0);""")
cur.execute("""CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        subject TEXT, time TEXT, teacher_id INTEGER, class_id INTEGER, topic TEXT, homework TEXT);""")
cur.execute("""CREATE TABLE IF NOT EXISTS marks (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        lesson_id INTEGER, student_id INTEGER, teacher_id INTEGER);""")
cur.execute("""CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, 
        lesson_id INTEGER, student_id INTEGER, teacher_id INTEGER, type INTEGER DEFAULT 0);""")


def databaserequest(text, params=None, commit=False):
    dbrequest = cur.execute(f"""{text}""", params)
    if not commit:
        return dbrequest.fetchall()
    else:
        con.commit()
    return True


def render_template(template, title="", **kwargs):
    logged = False
    acctype = 0
    if request.cookies.get("id"):
        logged = True
        acctype = int(request.cookies.get("acctype"))
        print(acctype)
    return flask.render_template(template, title=title, logged=logged, acctype=acctype, **kwargs)


@app.route('/')
def main():
    return render_template('main.html', title="Добро пожаловать!")


@app.route('/login')
def login():
    if request.cookies.get("id"):
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
            result = databaserequest("SELECT * FROM accounts WHERE yandex_id = ?", params=[accinfo.get("id")])
            print(result)
            if len(result) == 0:
                databaserequest("INSERT INTO accounts (login, yandex_id, first_name, last_name) VALUES (?, ?, ?, ?)",
                                params=[accinfo.get("login"), accinfo.get("id"), accinfo.get("first_name"),
                                        accinfo.get("last_name")], commit=True)
                print(
                    f'Зарегистрирован новый аккаунт: [{cur.lastrowid}] {accinfo.get("first_name")} {accinfo.get("last_name")} ({accinfo.get("login")} | {accinfo.get("id")})')
                dbaccinfo = [(cur.lastrowid, accinfo.get("login"), accinfo.get("id"), 0, accinfo.get("first_name"),
                              accinfo.get("last_name"))]
            else:
                dbaccinfo = databaserequest("SELECT * FROM accounts WHERE yandex_id = ?", params=[accinfo.get("id")])
                print(dbaccinfo)
            resp = app.make_response(render_template("process.html", title="Авторизация...", redirect="/account"))
            resp.set_cookie('id', f'{accinfo.get("id")}', max_age=2592000)
            resp.set_cookie('acctype', f'{dbaccinfo[0][3]}', max_age=2592000)
            return resp
        return redirect(
            "https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")
    return redirect("https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")


@app.route('/account')
def account():
    if request.cookies.get("id"):
        accinfo = databaserequest("SELECT * FROM accounts WHERE yandex_id = ?", params=[request.cookies.get("id")])
        print(accinfo[0])
        if len(accinfo) == 0:
            return redirect('/quit')
        resp = app.make_response(render_template("account.html", title="Личный кабинет", accinfo=accinfo[0]))
        resp.set_cookie('acctype', f'{accinfo[0][3]}', max_age=2592000)
        return resp
    else:
        return redirect('/login')


@app.route('/schedule')
def schedule():
    return render_template("schedule.html", title="Расписание", startdate="03 апреля 2023 года", enddate="09 апреля 2023 года", date="Понедельник 03 апреля 2023 года")


@app.route('/quit')
def quit():
    if request.cookies.get("id"):
        resp = app.make_response(render_template("main.html", title="Добро пожаловать!"))
        resp.set_cookie('id', "None", max_age=0)
        return resp
    else:
        return redirect('/login')


@app.route('/setadmindostup')
def setadmindostup():
    sql = f"UPDATE accounts SET {request.args.get('column')} = '{request.args.get('value')}' WHERE {request.args.get('column_where')} == '{request.args.get('value_where')}'"
    databaserequest(sql, params=[], commit=True)
    return sql


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', title="Страница не найдена", error='Извините, мы не можем найти данную страницу!'), 404


@app.errorhandler(500)
def on_error(e):
    return render_template('error.html', title="Произошла ошибка", error='Извините, произошла ошибка при выполнении запроса!'), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    con.close()
