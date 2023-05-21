# Яндекс.Дневник
### Электронный дневник на Python
**Возможности:**</br>
- Авторизация через аккаунт Яндекс (Яндекс ID).</br>
- С аккаунта со статусом «Учитель»:</br>
-- создание урока</br>
-- выставление оценок</br>
-- изменение/добавление информации об уроке</br>
- С аккаунта со статусом «Ученик»:</br>
-- просмотр уроков, созданных учителем</br>
-- просмотр своих оценок, выставленных учителем</br>
-- просмотр информации о уроке, указанной учителем</br>
- С аккаунта со статусом «Администратор»:</br>
-- управление аккаунтами (изменение типа аккаунта, назначение класса и удаление аккаунта)</br>
-- управление классами (назначение/изменение классного руководителя и удаление класса)</br>
- Уведомления об оценках и новых уроках через Telegram. </br>
- Связь с учителем или учеником через Telegram.</br>

**Основные библиотеки:**</br>
- SQLite3 (https://docs.python.org/3/library/sqlite3.html)</br>
- Flask (https://flask.palletsprojects.com)</br>
- python-telegram-bot (https://docs.python-telegram-bot.org)</br>

**Техническая часть проекта:**</br>
- Сайт</br>
    -- Главная страница</br>
    -- Страница авторизации</br>
    -- Рабочая среда (зависит от типа учётной записи): Ученик / Учитель / Администратор</br>
    -- API для Telegram Bot`а</br>
    -- Страницы с ошибками.</br>
- Telegram Bot</br>

**Настройка под себя:**
- Авторизация через Яндекс.ID:
    Поменяйте слова "КЛИЕНТID" и "КЛИЕНТСЕКРЕТ" на свои client_id и client_secret API Яндекс.ID.
- Telegram Bot:
    Поменяйте слово "APIКЛЮЧ" в файлах bot.py и telegramapi.py на свой API ключ бота Telegram.

**Материалы и команда разработки:**</br>
- Проект – Глазунов Никита</br>
- Мотивация и поддержка – Ложков Кирилл Германович</br>
- Все картинки, доступные для общего пользования, взяты из сети Интернет. </br>
- Права на шрифт «Yandex Sans» принадлежат ООО «Яндекс» (https://ru.wikipedia.org/wiki/Yandex_Sans).</br>

*Все права на бренд ЯНДЕКС принадлежат ООО «Яндекс».</br>
Сервис «Яндекс.Дневник» не является официальным сервисом ООО «Яндекс».</br>
Сервис «Яндекс.Дневник» не доступен для общего пользования.</br>*
