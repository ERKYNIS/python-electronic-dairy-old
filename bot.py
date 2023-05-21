import logging
import requests

from telegram.ext import Application, MessageHandler, filters, ConversationHandler, CommandHandler


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


async def checkauth(update, context):
    testaccount = requests.get(f"http://yandex-diary-python.glitch.me/api/getuser?chat_id="
                               f"{update.message.chat.id}").json()
    if testaccount['error']:
        if 'account' in context.user_data:
            context.user_data.pop('account')
        return False
    else:
        context.user_data['account'] = testaccount['account']
        return True


async def start(update, context):
    await update.message.reply_text(
        "Здравствуйте!\n"
        "Авторизируйтесь, используя команду \"/link\"")


async def help(update, context):
    await update.message.reply_text(
        "<strong>Помощь по командам</strong>:\n"
        "Привязать аккаунт -> /link\nОтвязать аккаунт -> /quit\nПрофиль -> /profile\n"
        "Отправить сообщение -> /message", parse_mode='html')


async def link(update, context):
    await checkauth(update, context)
    if "account" in context.user_data:
        account = context.user_data['account']
        await update.message.reply_text(f"К вашему аккаунту уже привязан аккаунт {account[4]} {account[5]}!")
    elif len(context.args) > 0:
        testaccount = requests.get(f"http://yandex-diary-python.glitch.me/api/login?code={context.args[0]}"
                                   f"&tgid={update.message.chat.id}&"
                                   f"tgusername={update.message.from_user.username}").json()
        if 'error' in testaccount:
            await update.message.reply_text(testaccount['error'])
        else:
            context.user_data['account'] = testaccount['account']
            await update.message.reply_text(testaccount['message'])
    else:
        await update.message.reply_text("Используйте -> \"/link <секретный код с сайта>\"")


async def profile(update, context):
    await checkauth(update, context)
    if "account" not in context.user_data:
        await update.message.reply_text("Вы не авторизированы! Используйте команду \"/link\".")
    else:
        account = context.user_data['account']
        acctypes = ["Пользователь", "Ученик", "Учитель", "Администратор"]
        if account[7] != 0:
            klass = requests.get(f"http://yandex-diary-python.glitch.me/api/getclass?id={account[7]}").json()['class']
            klass = f'{klass[1]}{klass[2]}'
        else:
            klass = 'Не указан'
        await update.message.reply_text(f"{account[4]} {account[5]} ({account[1]})\n\nРоль: "
                                        f"{acctypes[account[3]]}\nКласс: {klass}")


async def quit(update, context):
    await checkauth(update, context)
    if "account" not in context.user_data:
        await update.message.reply_text("Вы не авторизированы! Используйте команду \"/link\".")
    else:
        context.user_data.pop('account')
        await update.message.reply_text("Вы вышли из аккаунта!")


async def newmessage(update, context):
    await checkauth(update, context)
    if "account" not in context.user_data:
        await update.message.reply_text("Вы не авторизированы! Используйте команду \"/link\".")
        return ConversationHandler.END
    else:
        account = context.user_data['account']
        if account[7] == 0:
            await update.message.reply_text(
                "Администрация электронного дневника должна определить вас в класс, прежде чем вы сможете отправлять "
                "сообщения!")
            return ConversationHandler.END
        elif account[3] == 1:
            teacher = requests.get(f"http://yandex-diary-python.glitch.me/api/getteacher?id={account[7]}").json()
            if not teacher['error']:
                await update.message.reply_text("Введите сообщение для своего учителя.\nЕсли вы хотите отменить "
                                                "отправку сообщения, используйте \"/stopmessage\".")
                return 1
            else:
                await update.message.reply_text(f"В данный момент ваш учитель не принимает сообщения!")
                return ConversationHandler.END
        else:
            await update.message.reply_text("Введите Yandex ID ученика, которому хотите написать сообщение.\nНайти "
                                            "Yandex ID можно в разделе \"Мой класс\".")
            return 1


async def newmessage_1(update, context):
    account = context.user_data['account']
    if account[3] == 1:
        requests.get(f"http://yandex-diary-python.glitch.me/api/sendmessage?id={account[7]}&message="
                     f"{update.message.text}&student={account[4]} {account[5]}")
        await update.message.reply_text(f"Сообщение отправлено!")
        return ConversationHandler.END
    else:
        student = requests.get(f"http://yandex-diary-python.glitch.me/api/getstudent?id={update.message.text}&class="
                               f"{account[7]}").json()
        if not student['error']:
            context.user_data['temp'] = update.message.text
            await update.message.reply_text(f"Введите сообщение для {student['student'][4]} {student['student'][5]}."
                                            f"\nЕсли вы хотели отправить другому ученику, используйте команду "
                                            f"\"/stopmessage\".")
            return 2
        else:
            await update.message.reply_text(f"Вы ввели неверный Yandex ID\nТакже, возможно у ученика не привязан "
                                            f"Telegram аккаунт или он учится не в вашем классе.")
            return 1


async def newmessage_2(update, context):
    requests.get(f"http://yandex-diary-python.glitch.me/api/sendmessage?id={context.user_data['temp']}"
                 f"&message={update.message.text}&teacher=true")
    await update.message.reply_text(f"Сообщение отправлено!")
    return ConversationHandler.END


async def stopmessage(update, context):
    await update.message.reply_text("Отправка сообщения отменена.")
    return ConversationHandler.END


def startbot():
    application = Application.builder().token("APIКЛЮЧ").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('message', newmessage)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, newmessage_1)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, newmessage_2)]
        },

        fallbacks=[CommandHandler('stopmessage', stopmessage)]
    )

    application.add_handler(conv_handler)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('link', link))
    application.add_handler(CommandHandler('quit', quit))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('help', help))
    application.run_polling()

startbot()
