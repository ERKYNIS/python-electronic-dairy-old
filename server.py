import datetime
import os

import telegramapi
from urllib.parse import urlencode

from flask import Flask, render_template as rend_templ, request, redirect, flash
from requests import post

app = Flask(__name__)
app.secret_key = os.urandom(24)


def isloggin():
    if request.cookies.get("id"):
        return True
    return False


def render_template(template, title="", loginneed=False, typeneed=[0], **kwargs):
    if loginneed and not isloggin():
        return redirect('/login')
    elif typeneed[0] != 0 and int(request.cookies.get("acctype")) not in typeneed:
        return render_template('error.html', title="Ошибка",
                                     error='У вас нет доступа для просмотра данной страницы!')
    elif (2 in typeneed or 1 in typeneed) and telegramapi.databaserequest("SELECT * FROM accounts WHERE yandex_id = ?",
                                           params=[request.cookies.get("id")])[0][7] == 0:
        return render_template('error.html', title="Ошибка", error='Администрация электронного '
                                                                   'дневника должна определить вас в класс, '
                                                                   'прежде чем вы сможете просматривать данную '
                                                                   'страницу!')
    logged = False
    acctype = 0
    if request.cookies.get("id"):
        logged = True
        acctype = int(request.cookies.get("acctype"))
    return rend_templ(template, title=title, logged=logged, acctype=acctype,
                                 account=request.cookies.get("account"), avatar=request.cookies.get("avatarid"),
                                 **kwargs)


@app.route('/')
def main():
    return render_template('main.html', title="Добро пожаловать!")


@app.route('/login')
def login():
    if request.cookies.get("id"):
        return redirect("/account")
    if request.args.get("code"):
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
            dbaccinfo = telegramapi.databaserequest("SELECT * FROM accounts WHERE yandex_id = ?",
                                                    params=[accinfo.get("id")])
            if len(dbaccinfo) == 0:
                telegramapi.databaserequest("INSERT INTO accounts (login, yandex_id, first_name, last_name, avatar) "
                                "VALUES (?, ?, ?, ?, ?)",
                                params=[accinfo.get("login"), accinfo.get("id"), accinfo.get("first_name"),
                                        accinfo.get("last_name"), accinfo.get("default_avatar_id")], commit=True)
                print(f'Зарегистрирован новый аккаунт: [{telegramapi.cur.lastrowid}] {accinfo.get("first_name")} '
                      f'{accinfo.get("last_name")} ({accinfo.get("login")} | {accinfo.get("id")})')
                dbaccinfo = [(telegramapi.cur.lastrowid, accinfo.get("login"), accinfo.get("id"), 0,
                              accinfo.get("first_name"),
                              accinfo.get("last_name"), accinfo.get("default_avatar_id"))]
            else:
                telegramapi.databaserequest("UPDATE accounts SET first_name = ?, last_name = ?, avatar = ? WHERE yandex_id = ?",
                                params=[accinfo.get("first_name"), accinfo.get("last_name"),
                                        accinfo.get("default_avatar_id"), accinfo.get("id")], commit=True)
            resp = app.make_response(render_template("process.html", title="Авторизация...", redirect="/account"))
            resp.set_cookie('id', f'{accinfo.get("id")}', max_age=2592000)
            resp.set_cookie('account_id', f'{dbaccinfo[0][0]}', max_age=2592000)
            resp.set_cookie('acctype', f'{dbaccinfo[0][3]}', max_age=2592000)
            resp.set_cookie('account', f'{accinfo.get("first_name")} {accinfo.get("last_name")}', max_age=2592000)
            resp.set_cookie('avatarid', f'{accinfo.get("default_avatar_id")}', max_age=2592000)
            return resp
        return redirect(
            "https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")
    return redirect("https://oauth.yandex.ru/authorize?client_id=5e6a0be5bbfe4606be5c35a28e6fe741&response_type=code")


@app.route('/account', methods=['GET', 'POST'])
def account():
    if isloggin():
        accinfo = telegramapi.databaserequest("SELECT * FROM accounts WHERE yandex_id = ?",
                                              params=[request.cookies.get("id")])
        if len(accinfo) == 0:
            return redirect('/quit')
        if request.form.get('action') == "unlinkTelegram":
            telegramapi.databaserequest("UPDATE accounts SET tg_chat_id = ?, tg_username = ? WHERE yandex_id = ?",
                                        params=[None, None, request.cookies.get("id")], commit=True)
            telegramapi.sendmessage(accinfo[0][8], f"Ваш аккаунт больше не привязан к аккаунту {accinfo[0][4]} "
                                                f"{accinfo[0][5]}!")
            flash(f'Вы успешно отвязали свой аккаунт Telegram!', 'warning')
            return redirect('/account')
        resp = app.make_response(render_template("account.html", title="Личный кабинет", loginneed=True,
                                                 accinfo=accinfo[0], acctypes=["Пользователь", "Ученик", "Учитель",
                                                                               "Администратор"],
                                                 classinfo=telegramapi.databaserequest("SELECT * FROM classes "
                                                                                       "WHERE id = ?",
                                                                           params=[accinfo[0][7]])))
        resp.set_cookie('acctype', f'{accinfo[0][3]}', max_age=2592000)
        return resp
    else:
        return redirect('/login')


@app.route('/accounts', methods=["GET", "POST"])
def accounts():
    classes = telegramapi.databaserequest("SELECT * FROM classes")
    accounts = telegramapi.databaserequest("SELECT * FROM accounts")
    editacc = [[0, "Имя Фамилия", 0]]
    acctypes = ["Пользователь", "Ученик", "Учитель", "Администратор"]
    if request.args.get("id") and request.args.get("action"):
        editacc = telegramapi.databaserequest("SELECT * FROM accounts WHERE id = ?", params=[request.args.get("id")])
    if request.method == "POST":
        action = request.form.get("action")
        account = request.form.get("account").split(' | ')
        if action == "editType":
            telegramapi.databaserequest("UPDATE accounts SET acctype = ? WHERE id = ?",
                                        params=[int(request.form.get("newtype")), int(request.form.get("accid"))],
                            commit=True)
            flash(f'Вы успешно изменили тип аккаунта {account[0]} {account[1]} (№{account[2]} | {account[3]}) '
                  f'на {acctypes[int(request.form.get("newtype"))]}!', 'success')
            if request.form.get("accid") == request.cookies.get("account_id"):
                return redirect('/quit')
            return redirect('/accounts')
        elif action == "editClass":
            telegramapi.databaserequest("UPDATE accounts SET class = ? WHERE id = ?",
                                        params=[int(request.form.get("newclass")), int(request.form.get("accid"))],
                            commit=True)
            newclass = "Не указан"
            if int(request.form.get("newclass")) != 0:
                newclass = f'{classes[int(request.form.get("newclass")) - 1][1]} ' \
                           f'{classes[int(request.form.get("newclass")) - 1][2]}'
            flash(f'Вы успешно изменили класс аккаунта {account[0]} {account[1]} (№{account[2]} | {account[3]}) '
                  f'на {newclass}!', 'success')
            return redirect('/accounts')
        elif action == "delete":
            if account[4] != "3":
                telegramapi.databaserequest("DELETE FROM accounts WHERE id = ?",
                                            params=[int(request.form.get("accid"))], commit=True)
                flash(f'Вы успешно удалили аккаунт {account[0]} {account[1]} (№{account[2]} | {account[3]})!',
                      'warning')
                return redirect('/accounts')
            else:
                flash(
                    f'Вы не можете удалить аккаунт {account[0]} {account[1]} (№{account[2]} | {account[3]}), '
                    f'так как это Администратор!', 'danger')
    resp = app.make_response(render_template("admin/accounts.html", title="Аккаунты", loginneed=True,
                                             accounts=accounts, acctypes=acctypes, editacc=editacc[0], classes=classes))
    return resp


@app.route('/classes', methods=["GET", "POST"])
def classes():
    classes = telegramapi.databaserequest("SELECT * FROM classes")
    for clas in classes:
        clasindex = classes.index(clas)
        clas = list(clas)
        testteacher = telegramapi.databaserequest("SELECT * FROM accounts WHERE class = ? ORDER BY acctype DESC",
                                                  params=[clas[0]])
        if len(testteacher) != 0:
            clas.append(testteacher[0])
            classes[clasindex] = tuple(clas)
        else:
            clas.append((0, 0, 0, 0, "Не", "указан", 0, 0))
        classes[clasindex] = tuple(clas)
    teachers = telegramapi.databaserequest("SELECT * FROM accounts WHERE acctype = 2")
    editclass = [[0, "А", 1, [0, "Имя Фамилия", 0]]]
    if request.args.get("id") and request.args.get("action"):
        editclass = telegramapi.databaserequest("SELECT * FROM classes WHERE id = ?", params=[request.args.get("id")])
        testteacher = telegramapi.databaserequest("SELECT * FROM accounts WHERE class = ?",
                                                  params=[request.args.get("id")])
        clas = list(editclass[0])
        if len(testteacher) != 0:
            clas.append(testteacher[0])
        else:
            clas.append(0)
        editclass[0] = tuple(clas)
    if request.method == "POST":
        action = request.form.get("action")
        if action != "createClass":
            classinfo = request.form.get("class").split(' | ')

        if action == "editTeacher":
            if request.form.get("newteacher") != "0":
                testteacher = telegramapi.databaserequest("SELECT * FROM accounts WHERE id = ?",
                                              params=[request.form.get("newteacher")])
                telegramapi.databaserequest("UPDATE accounts SET class = ? WHERE id = ?",
                                params=[int(request.form.get("classid")), int(request.form.get("newteacher"))],
                                commit=True)
            else:
                testteacher = [(0, 0, 0, 2, "Не", "указан", 0, 0)]
                if request.form.get("thisteacher") != "0":
                    telegramapi.databaserequest("UPDATE accounts SET class = 0 WHERE id = ?",
                                    params=[int(request.form.get("thisteacher"))],
                                    commit=True)
            if testteacher[0][7] == 0:
                telegramapi.databaserequest("UPDATE accounts SET class = ? WHERE id = ?",
                                params=[int(request.form.get("classid")), int(request.form.get("newteacher"))],
                                commit=True)
                flash(f'Вы успешно изменили классного руководителя {classinfo[1]} {classinfo[2]} (№{classinfo[0]}) '
                      f'на {testteacher[0][4]} {testteacher[0][5]}!', 'success')
                return redirect('/classes')
            else:
                flash(f'Вы не можете назначить {testteacher[0][4]} {testteacher[0][5]} руководителем класса '
                      f'{classinfo[1]} {classinfo[2]}, так как он уже является классный руководителем другого класса!',
                      'danger')
        elif action == "createClass":
            telegramapi.databaserequest("INSERT INTO classes('litter', 'class') VALUES (?, ?)",
                            params=[request.form.get("num"), request.form.get("litter")], commit=True)
            if request.args.get("teacher") != 0:
                telegramapi.databaserequest("UPDATE accounts SET class = ? WHERE id = ?",
                                            params=[telegramapi.cur.lastrowid,
                                                                                      request.form.get("teacher")],
                                commit=True)
            flash(f'Вы успешно создали класс {request.form.get("num")} {request.form.get("litter")}!', 'success')
            return redirect('/classes')
        elif action == "delete":
            telegramapi.databaserequest("DELETE FROM classes WHERE id = ?",
                                        params=[int(request.form.get("classid"))], commit=True)
            telegramapi.databaserequest("UPDATE accounts SET class = 0 WHERE class = ?",
                                        params=[int(request.form.get("classid"))],
                            commit=True)
            flash(f'Вы успешно удалили класс {classinfo[1]} {classinfo[2]} (№{classinfo[0]})!', 'warning')
            return redirect('/classes')
    resp = app.make_response(render_template("admin/classes.html", title="Классы", loginneed=True, typeneed=[3],
                                             classes=classes, teachers=teachers, editclass=editclass[0]))
    return resp


@app.route('/class')
def teacherclass():
    accounts = telegramapi.databaserequest("SELECT * FROM accounts WHERE class = ? AND yandex_id != ?",
                               params=[telegramapi.databaserequest("SELECT class FROM accounts WHERE yandex_id = ?",
                                                       params=[request.cookies.get("id")])[0][0],
                                       request.cookies.get("id")])
    resp = app.make_response(
        render_template("admin/accounts.html", title="Мой класс", loginneed=True, typeneed=[2], accounts=accounts))
    return resp


@app.route('/diary', methods=["GET", "POST"])
def diary():
    isteacher = False
    if int(request.cookies.get("acctype")) == 2:
        isteacher = True
    lessons = [[], [], [], [], [], [], []]
    month = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
             "декабря"]
    createdate = 0
    requestdate = datetime.date.today()
    if request.args.get('date'):
        requestdate = datetime.datetime.strptime(request.args.get('date'), "%Y-%m-%d").date()
    start = requestdate - datetime.timedelta(days=requestdate.weekday())
    dates = []
    while len(dates) < 7:
        dateformated = str(start + datetime.timedelta(days=len(dates))).split("-")
        date = f"{dateformated[2]}.{dateformated[1]}.{dateformated[0]}"
        dates.append(f"{dateformated[2]} {month[int(dateformated[1]) - 1]} {dateformated[0]} года")

        for thisdatelesson in telegramapi.databaserequest("SELECT * FROM lessons WHERE datetime LIKE ? AND "
                                                          "class_id = ? "
                                              "ORDER BY datetime",
                                              params=[f'%{date}%',
                                                      telegramapi.databaserequest("SELECT class FROM accounts "
                                                                                  "WHERE yandex_id = ?",
                                                                      params=[request.cookies.get("id")])[0][0]]):
            if not isteacher:
                thisdatelesson = list(thisdatelesson)
                testmarks = telegramapi.databaserequest("SELECT id, mark FROM marks WHERE lesson_id = ? AND "
                                                        "student_id = ?",
                                            params=[thisdatelesson[0], request.cookies.get("account_id")])
                if len(testmarks) != 0:
                    thisdatelesson.append(testmarks)
                else:
                    thisdatelesson.append([])
                thisdatelesson = tuple(thisdatelesson)
            lessons[len(dates) - 1].append(thisdatelesson)

    if request.form.get('action'):
        action = request.form.get('action')
        if action == "addLesson":
            klass = telegramapi.databaserequest("SELECT class FROM accounts WHERE yandex_id = ?",
                                                    params=[request.cookies.get("id")])[0][0]
            telegramapi.databaserequest("INSERT INTO lessons('subject', 'datetime', 'class_id', 'topic', 'homework') "
                                        "VALUES "
                            "(?, ?, ?, ?, ?)",
                            params=[request.form.get("subject"), f'{request.form.get("date")} '
                                                                 f'{request.form.get("time")}', klass,
                                    request.form.get("topic"), request.form.get("homework")], commit=True)
            flash(f'Вы успешно создали урок по предмету {request.form.get("subject")} ({request.form.get("date")} '
                  f'{request.form.get("time")})!', 'success')
            telegramapi.sendclassmessage(klass, f"Создан новый урок по предмету {request.form.get('subject')}\nДата: "
                                                f"{request.form.get('date')}\n\nТема: {request.form.get('topic')}\n"
                                                f"Домашнее задание: {request.form.get('homework')}")
            return redirect('/diary')
    elif request.args.get('action') == "removeLesson":
        lessoninfo = telegramapi.databaserequest("SELECT * FROM lessons WHERE id = ?", params=[request.args.get('id')])
        if len(lessoninfo) > 0:
            lessoninfo = lessoninfo[0]
            telegramapi.databaserequest("DELETE FROM lessons WHERE id = ?", params=[request.args.get('id')],
                                        commit=True)
            flash(f'Вы успешно удалили урок по предмету {lessoninfo[1]} ({lessoninfo[2]})!', 'warning')
            return redirect('/diary')
        else:
            flash(f'Произошла ошибка при получении информации об уроке!', 'danger')
    elif request.args.get('createdate'):
        createdate = request.args.get('createdate').split(' ')
        createdate[1] = str(month.index(createdate[1]) + 1)
        if len(createdate[1]) < 2:
            createdate[1] = '0' + createdate[1]
        createdate.remove('года')
        createdate = '.'.join(createdate)
    return render_template("student/diary.html", title="Журнал", loginneed=True, typeneed=[1, 2], startdate=dates[0],
                           enddate=dates[len(dates) - 1], dates=dates,
                           week=["Понедельник", "Вторник", "Среда", "Четверг",
                                 "Пятница", "Суббота", "Воскресенье"],
                           nextweek=start + datetime.timedelta(weeks=1),
                           previousweek=start - datetime.timedelta(weeks=1),
                           isteacher=isteacher, createdate=createdate, lessons=lessons)


@app.route('/lesson/<int:lessonid>', methods=["GET", "POST"])
def lesson(lessonid):
    editpeople = [0, "Имя Фамилия", 0, 0, 0, 0, 0, 0, 0, 0, [[0, 0]]]
    lessoninfo = telegramapi.databaserequest("SELECT * FROM lessons WHERE id = ?", params=[lessonid])
    if len(lessoninfo) <= 0:
        return redirect('/diary')
    peoples = telegramapi.databaserequest("SELECT * FROM accounts WHERE class = ? AND yandex_id != ?", params=[
        telegramapi.databaserequest("SELECT class FROM accounts WHERE yandex_id = ?",
                                    params=[request.cookies.get("id")])[0][0],
        request.cookies.get("id")])
    for people in peoples:
        accindex = peoples.index(people)
        people = list(people)

        testmarks = telegramapi.databaserequest("SELECT id, mark FROM marks WHERE lesson_id = ? AND student_id = ?",
                                    params=[lessonid, people[0]])
        if len(testmarks) != 0:
            people.append(testmarks)
        else:
            people.append([])

        peoples[accindex] = tuple(people)
    if request.args.get('peopleid'):
        editpeople = list(telegramapi.databaserequest("SELECT * FROM accounts WHERE id = ?",
                                          params=[request.args.get("peopleid")])[0])
        if request.args.get('markid'):
            editpeople.append(telegramapi.databaserequest("SELECT id, mark FROM marks WHERE id = ?",
                                              params=[request.args.get("markid")])[0])
    elif request.form.get('action'):
        if request.form.get('action') == "addMark":
            telegramapi.databaserequest("INSERT INTO marks('lesson_id', 'student_id', 'mark') VALUES (?, ?, ?)",
                            params=[lessonid, request.form.get("peopleid"), request.form.get("mark")], commit=True)
            flash(f'Вы выставили оценку "{request.form.get("mark")}" ученику {request.form.get("people")} '
                  f'на урок по предмету {lessoninfo[0][1]} ({lessoninfo[0][2]})!', 'success')
            telegramapi.sendusermessage(request.form.get("peopleid"), f"Новая оценка:\n\nУрок: {lessoninfo[0][1]} "
                                                                      f"({lessoninfo[0][2]})\nОценка: "
                                                                      f"{request.form.get('mark')}")
            return redirect(f'/lesson/{lessonid}')
        elif request.form.get('action') == "editMark":
            if request.form.get("newmark") != "0":
                telegramapi.databaserequest("UPDATE marks SET mark = ? WHERE id = ?",
                                params=[request.form.get("newmark"), request.form.get("markid")], commit=True)
                flash(f'Вы изменили оценку на "{request.form.get("newmark")}" ученику {request.form.get("people")}, '
                      f'выставленную на урок по предмету {lessoninfo[0][1]} ({lessoninfo[0][2]})!', 'success')
                telegramapi.sendusermessage(request.form.get("peopleid"), f"Изменена оценка:\n\nУрок: {lessoninfo[0][1]} "
                                                                          f"({lessoninfo[0][2]})\nОценка: "
                                                                          f"{request.form.get('newmark')}")
            else:
                telegramapi.databaserequest("DELETE FROM marks WHERE id = ?", params=[request.form.get("markid")],
                                            commit=True)
                flash(f'Вы убрали оценку ученику {request.form.get("people")}, выставленную на урок по предмету '
                      f'{lessoninfo[0][1]} ({lessoninfo[0][2]})!', 'success')
                telegramapi.sendusermessage(request.form.get("peopleid"), f"Убрана оценка:\n\nУрок: {lessoninfo[0][1]} "
                                                                          f"({lessoninfo[0][2]})")
            return redirect(f'/lesson/{lessonid}')
        elif request.form.get('action') == "editInfo":
            telegramapi.databaserequest("UPDATE lessons SET topic = ?, homework = ? WHERE id = ?",
                            params=[request.form.get("topic"), request.form.get("homework"), lessonid], commit=True)
            flash(f'Вы обновили информацию об уроке по предмету {lessoninfo[0][1]} ({lessoninfo[0][2]})!', 'success')
            return redirect(f'/lesson/{lessonid}')
    if len(editpeople) < 11:
        editpeople.append([[]])
    return render_template("teacher/lesson.html", title=f'Урок - {lessoninfo[0][1]} {lessoninfo[0][2]}', typeneed=[2],
                           lesson=lessoninfo[0], peoples=peoples, loginneed=True, editpeople=editpeople)


@app.route('/quit')
def accountquit():
    resp = app.make_response(redirect('/'))
    resp.set_cookie('id', "None", max_age=0)
    resp.set_cookie('account_id', "None", max_age=0)
    resp.set_cookie('account', "None", max_age=0)
    resp.set_cookie('avatarid', "None", max_age=0)
    resp.set_cookie('acctype', "None", max_age=0)
    return resp


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', title="Страница не найдена",
                           error='Извините, мы не можем найти данную страницу!'), 404


@app.errorhandler(500)
def on_error(e):
    print("ОШИБКА:\n", e)
    return render_template('error.html', title="Произошла ошибка",
                           error='Извините, произошла ошибка при выполнении запроса!'), 500


if __name__ == '__main__':
    app.register_blueprint(telegramapi.blueprint)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    telegramapi.con.close()
