import sqlite3

import requests
from flask import redirect, jsonify, request, Blueprint

blueprint = Blueprint(
    'telegram_api',
    __name__,
    template_folder='templates'
)

BOTTOKEN = 'ТОКЕН БОТА TELEGRAM'

con = sqlite3.connect("database.db", check_same_thread=False)
cur = con.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, yandex_id TEXT, 
acctype INTEGER DEFAULT (0), first_name TEXT, last_name TEXT, avatar TEXT, class INTEGER DEFAULT (0), tg_chat_id TEXT 
NULL, tg_username TEXT NULL);""")
cur.execute("""CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY AUTOINCREMENT, litter TEXT, class 
INTEGER);""")
cur.execute("""CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, datetime TEXT, 
class_id INTEGER, topic TEXT, homework TEXT);""")
cur.execute("""CREATE TABLE IF NOT EXISTS marks (id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER, 
student_id INTEGER, mark INTEGER);""")
cur.execute("""CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER, 
student_id INTEGER, attendance INTEGER);""")


def sendmessage(chat_id, message):
    return requests.get(f'https://api.telegram.org/bot{BOTTOKEN}/sendMessage?chat_id=' + str(chat_id) + '&parse_mode=Markdown&text=' + message).json()


def sendusermessage(id, message):
    account = databaserequest("SELECT * FROM accounts WHERE id = ? AND LENGTH(tg_chat_id) >= 1", params=[id])
    if len(account) > 0:
        return requests.get(f'https://api.telegram.org/bot{BOTTOKEN}/sendMessage?chat_id=' + str(account[0][8]) + '&parse_mode=Markdown&text=' + message).json()


def sendclassmessage(id, message):
    peoples = databaserequest("SELECT * FROM accounts WHERE class = ? AND LENGTH(tg_chat_id) >= 1", params=[id])
    if len(peoples) > 0:
        for people in peoples:
            return requests.get(f'https://api.telegram.org/bot{BOTTOKEN}/sendMessage?chat_id=' + str(people[8]) + '&parse_mode=Markdown&text=' + message).json()


def databaserequest(text, params=None, commit=False):
    if params is None:
        params = []
    dbrequest = cur.execute(f"""{text}""", params)
    if not commit:
        return dbrequest.fetchall()
    else:
        con.commit()
    return True


@blueprint.route('/api/<method>')
def telegramapi(method):
    if method:
        if method == "login":
            testaccount = databaserequest("SELECT * FROM accounts WHERE avatar = ?", params=[request.args.get("code")])
            if len(testaccount) > 0:
                if not testaccount[0][8]:
                    databaserequest("UPDATE accounts SET tg_chat_id = ?, tg_username = ? WHERE avatar = ?",
                                                  params=[request.args.get("tgid"), request.args.get("tgusername"),
                                                          request.args.get("code")], commit=True)
                    return jsonify({'account': testaccount[0], 'message': f'Добро пожаловать, {testaccount[0][4]} {testaccount[0][5]}!'})
                else:
                    return jsonify({'error': 'К данному аккаунту уже привязан другой аккаунт Telegram!'})
            else:
                return jsonify({'error': 'Неверный секретный ключ!'})
        elif method == "quit":
            databaserequest("UPDATE accounts SET tg_chat_id = ?, tg_username = ? WHERE id = ?", params=[None, None, request.args.get("id")], commit=True)
            return jsonify({'OK': 'OK'})
        elif method == "getuser":
            testaccount = databaserequest("SELECT * FROM accounts WHERE tg_chat_id = ?",
                                          params=[request.args.get("chat_id")])
            if len(testaccount) > 0:
                return jsonify({'error': False, 'account': testaccount[0]})
            else:
                return jsonify({'error': True})
        elif method == "getclass":
            testclass = databaserequest("SELECT * FROM classes WHERE id = ?",
                                          params=[request.args.get("id")])
            if len(testclass) > 0:
                return jsonify({'error': False, 'class': testclass[0]})
            else:
                return jsonify({'error': True})
        elif method == "getteacher":
            teacher = databaserequest("SELECT * FROM accounts WHERE acctype = 2 AND class = ? AND LENGTH(tg_chat_id) >= 1", params=[request.args.get("id")])
            if len(teacher) > 0:
                return jsonify({'error': False, 'teacher': teacher[0]})
            else:
                return jsonify({'error': True})
        elif method == "getstudent":
            student = databaserequest(
                "SELECT * FROM accounts WHERE class = ? AND yandex_id = ? AND LENGTH(tg_chat_id) >= 1",
                params=[request.args.get("class"), request.args.get("id")])
            if len(student) > 0:
                return jsonify({'error': False, 'student': student[0]})
            else:
                return jsonify({'error': True})
        elif method == "sendmessage":
            if 'teacher' in request.args:
                sendmessage(str(databaserequest("SELECT * FROM accounts WHERE yandex_id = ?", params=[request.args.get("id")])[0][8]), f"Вам новое сообщение от вашего учителя:\n\n" + request.args.get("message"))
            else:
                sendmessage(str(databaserequest("SELECT * FROM accounts WHERE acctype = 2 AND class = ? AND LENGTH(tg_chat_id) >= 1", params=[request.args.get("id")])[0][8]), f"Вам новое сообщение от вашего ученика {request.args.get('student')}:\n\n" + request.args.get("message"))
            return 'OK'
    else:
        return redirect('/')