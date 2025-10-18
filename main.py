from datetime import datetime
import json
from os.path import exists
from os import kill, getpid

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


def timeformat():
    et = datetime.now()
    return (f'{str(et.day).rjust(2, "0")}.{str(et.month).rjust(2, "0")}' +
            f'.{et.year} {et.hour}:{str(et.minute).rjust(2, "0")}')

class Bot:
    start_message = """\
<b>Привет!</b>
Этот бот - место для обмена фотографиями"""
    menu_message = """\
<b>Привет, {}!</b>
Начните с поста своего изображения (просто пришлите фото сюда)
или откройте обменник с помощью /menu"""
    sign_up_message = """
<b>Для использования неограниченной версии бота необходимо выбрать никнейм.</b>
Можно выбрать один из предложенных вариантов или прислать свой. Никнейм может быть изменён позже"""
    help_message = """\
<b>Команды:</b>
/start - Перезапустить бота
/help - Отобразить список команд (этот)

/menu - Открыть обменник
/nickname - Обновить никнейм"""
    nick_syntax_warning = """\
<b>Неверный формат никнейма</b>
Никнейм должен:
- состоять из латинских букв или цифр
- быть в длину не меньше 4 и не больше 32
Повторите попытку"""
    nick_exists_warning = """\
<b>Никнейм занят</b>
Никнейм - это уникальное имя пользователя, по которому его можно идентифицировать. \
Поэтому никнеймы не должны повторяться
Повторите попытку"""

    def __init__(self, api_token):
        self.bot = telebot.TeleBot(api_token)
        self.udb_path = "users_data.json"
        self.cdb_path = "content.json"
        self.commands_functions = {
            "help": {
                "get-text": lambda usr: self.help_message
            }
        }
        self.application_data = {
        }
        if not exists(self.udb_path):
            with open(self.udb_path, 'w') as udf:
                json.dump({"auth": [],
                           "users": {}, "sessions": {}}, udf, indent=2)
        if not exists(self.cdb_path):
            with open(self.cdb_path, 'w') as cdf:
                json.dump({}, cdf, indent=2)
        print()

    def get_session(self, user):
        with open(self.udb_path) as udb:
            udb_data = json.load(udb)
            session_data = None if str(user) not in udb_data['sessions'] else \
                udb_data['sessions'][str(user)]
        return session_data

    def set_session(self, user, **values):
        with open(self.udb_path) as udb:
            udb_data = json.load(udb)
        if str(user) not in udb_data['sessions']:
            udb_data['sessions'][str(user)] = {**values}
        else:
            for name, value in values.items():
                udb_data['sessions'][str(user)][name] = value
        with open(self.udb_path, 'w') as udb:
            json.dump(udb_data, udb, indent=2)

    def get_users(self):
        with open(self.udb_path) as udb:
            udb_data = json.load(udb)
        return udb_data['users']

    def set_users(self, users):
        with open(self.udb_path) as udb:
            udb_data = json.load(udb)
        udb_data['users'] = users
        with open(self.udb_path, 'w') as udb:
            json.dump(udb_data, udb, indent=2)

    def get_content(self):
        with open(self.cdb_path) as cdb:
            cdb_data = json.load(cdb)
        return cdb_data

    def set_content(self, content: dict):
        with open(self.cdb_path, 'w') as cdb:
            json.dump(content, cdb, indent=2)

    def main_window(self, cid):
        session = self.get_session(cid)
        content = self.get_content()
        users = self.get_users()

        if not content:
            self.bot.send_message(cid, "Здесь пока ничего нет. Начните выкладывать!")
            self.bot.delete_message(cid, session['inline'])
            return
        elif "select" not in session:
            select = min([int(x) for x in content])
            self.set_session(cid, select=select)
        else:
            if not session['select'] or session['select'] not in content:
                select = min([int(x) for x in content])
                self.set_session(cid, select=select)
            else:
                select = session['select']
        photo = content[str(select)]
        liked = cid in photo['likes']
        text = f"""<b>{list(content.keys()).index(str(select)) + 1}/{len(content)}
Автор:</b> {users[str(photo['author'])]['nickname']}
<b>Опубликовано:</b> {photo['published']} (ID:{select})"""
        prev_av = min([int(x) for x in content]) < select
        next_av = max([int(x) for x in content]) > select

        markup = InlineKeyboardMarkup()
        buttons = []
        if prev_av:
            buttons.extend([
                InlineKeyboardButton("⏮️", callback_data="menu;oldest"),
                InlineKeyboardButton("◀️", callback_data="menu;prev")
            ])
        buttons.append(InlineKeyboardButton("❤️" if liked else "🩶", callback_data="menu;like"))
        if next_av:
            buttons.extend([
                InlineKeyboardButton("▶️", callback_data="menu;next" if next_av else None),
                InlineKeyboardButton("⏭️", callback_data="menu;newest" if next_av else None)
            ])
        markup.row(*buttons)
        if photo['author'] == cid:
            markup.row(InlineKeyboardButton('Удалить', callback_data="menu;del"))

        media = InputMediaPhoto(
            media=photo['photo'],
            caption=text,
            parse_mode='html'
        )
        self.bot.edit_message_media(media, cid, session['inline'], reply_markup=markup)

    def boot(self):
        print("[STATUS] Pending")
        self.bot.infinity_polling()

    def load_handlers(self):
        print("[STATUS] Loading handlers...")

        @self.bot.callback_query_handler()
        def dm_call(call):
            cid = call.message.chat.id
            msg = call.message
            command, *data = call.data.split(';')
            session = self.get_session(str(cid))

            if command == 'photo':
                action = data[0]
                if action == 'cancel':
                    self.bot.delete_message(msg.chat.id, msg.id)
                    self.set_session(str(cid), photo=None)
                elif action == 'post':
                    content = self.get_content()
                    ind = 0
                    if content:
                        ind = max([int(x) for x in content]) + 1
                    content[str(ind)] = {
                        'photo': session['photo'],
                        'author': cid,
                        'likes': [],
                        'published': timeformat()
                    }
                    self.set_content(content)
                    self.bot.delete_message(cid, session['inline'])
                    self.bot.send_message(cid, "Изображение опубликовано. ID: {}".format(ind))
                    self.set_session(str(cid), photo=None, inline=None)

            elif command == 'menu':
                action = data[0]
                content = self.get_content()
                keys = [int(x) for x in content]
                if action == 'oldest':
                    self.set_session(cid, select=min(keys))
                elif action == 'prev':
                    self.set_session(cid, select=keys[keys.index(session['select']) - 1])
                elif action == 'next':
                    self.set_session(cid, select=keys[keys.index(session['select']) + 1])
                elif action == 'newest':
                    self.set_session(cid, select=max(keys))
                elif action == 'like':
                    if cid not in content[str(session['select'])]['likes']:
                        content[str(session['select'])]['likes'].append(cid)
                    else:
                        content[str(session['select'])]['likes'].remove(cid)
                    self.set_content(content)
                elif action == 'del':
                    content.pop(str(session['select']))
                    self.set_content(content)
                self.main_window(cid)


        @self.bot.message_handler(content_types=["photo"])
        def dm_photo(msg):
            cid = msg.from_user.id
            users = self.get_users()
            if str(cid) not in users:
                dm_start(msg)
            else:
                photo = max(msg.photo, key=lambda x: x.height)
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("Отмена", callback_data="photo;cancel"),
                           InlineKeyboardButton("Опубликовать", callback_data="photo;post"))
                new = self.bot.send_photo(msg.chat.id, photo=photo.file_id, caption="Опубликовать изображение?",
                                          reply_markup=markup)
                self.set_session(str(cid), photo=photo.file_id, inline=new.id)
                try:
                    self.bot.delete_message(msg.chat.id, msg.id)
                except:
                    pass

        @self.bot.message_handler(commands=["start"])
        def dm_start(msg):
            cid = msg.from_user.id
            users = self.get_users()
            self.set_session(cid, expect=None)
            session = self.get_session(cid)
            try:
                if "inline" in session:
                    self.bot.delete_message(cid, session["inline"])
            except:
                pass

            if str(cid) not in users:
                markup = ReplyKeyboardMarkup(resize_keyboard=True)
                buttons = []
                if msg.from_user.username:
                    buttons.append(KeyboardButton(msg.from_user.username))
                if msg.from_user.first_name:
                    buttons.append(KeyboardButton(msg.from_user.first_name))
                markup.add(*buttons)

                self.bot.send_message(msg.chat.id, self.start_message, parse_mode="html")
                self.bot.send_message(msg.chat.id, self.sign_up_message, parse_mode="html",
                                      reply_markup=markup)
                self.set_session(cid, expect="nickname")

            else:
                self.bot.send_message(msg.chat.id, self.menu_message.format(users[str(cid)]['nickname']),
                                      parse_mode="html")

        @self.bot.message_handler(commands=["help"])
        def dm_help(msg):
            self.bot.send_message(msg.chat.id, self.commands_functions["help"]["get-text"](msg.chat.id),
                                  parse_mode="html")

        @self.bot.message_handler(commands=["menu"])
        def dm_menu(msg):
            cid = msg.from_user.id
            users = self.get_users()
            if str(cid) not in users:
                dm_start(msg)
            else:
                session = self.get_session(cid)
                try:
                    if "inline" in session:
                        self.bot.delete_message(cid, session["inline"])
                except:
                    pass
                new = self.bot.send_message(cid, 'Секунду...')
                self.set_session(cid, inline=new.id)
                self.main_window(cid)

        @self.bot.message_handler(content_types=["text"])
        def dm_text(msg):
            cid = str(msg.from_user.id)
            session = self.get_session(cid)
            if session and session['expect']:
                expect = session['expect']

                if expect == 'nickname':
                    users = self.get_users()
                    if not (msg.text.isalnum() and 3 < len(msg.text) < 33):
                        self.bot.send_message(msg.chat.id, self.nick_syntax_warning , parse_mode="html")
                        return
                    if msg.text.lower() in [user['nickname'].lower() for user in users.values()]:
                        self.bot.send_message(msg.chat.id, self.nick_exists_warning, parse_mode="html")
                        return
                    if cid not in users:
                        users[cid] = {
                            "nickname": msg.text,
                            "created": timeformat()
                        }
                        self.set_session(cid, expect=None)
                        self.set_users(users)
                        self.bot.send_message(msg.chat.id, """<b>Добро пожаловать на Plumbum!</b>
Ваш никнейм: {}""".format(msg.text),
                                              reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode='html')
                        dm_start(msg)
                    else:
                        users[cid]["nickname"] = msg.text
                        self.set_session(cid, expect=None)
                        self.bot.send_message(msg.chat.id, "Никнейм обновлён",
                                              reply_markup=telebot.types.ReplyKeyboardRemove())


    def enable_admin_tools(self, master_password):
        print("[STATUS] Enabling ADMINTOOLS")
        self.application_data["AdminTools"] = {}
        self.application_data["AdminTools"]["password"] = master_password
        self.application_data["AdminTools"]["help"] = """
<i>## Admin Tools ##</i>
/auth {password} - get access to Admin Tools
/post {text} - send every user of this bot a message
/force_stop - stop the bot entirely
/quit_AT - quit admin tools
"""
        self.commands_functions["help"]["get-text"] = lambda usr: self.application_data["AdminTools"]["help"] \
            if check_auth(self, usr) else self.help_message

        def check_auth(self, usr):
            with open(self.udb_path) as udb:
                return usr in json.load(udb)["auth"]

        def new_auth(self, usr, close=False):
            with open(self.udb_path) as udb:
                udb_data = json.load(udb)
                udb_data["auth"] = list(set(udb_data["auth"] + [usr]))
                if close:
                    udb_data["auth"].remove(usr)
            with open(self.udb_path, 'w') as udb:
                json.dump(udb_data, udb)

        @self.bot.message_handler(commands=["auth"])
        def dm_at_auth(msg):
            if msg.text[6:] == self.application_data["AdminTools"]["password"]:
                new_auth(self, msg.from_user.id)
                self.bot.send_message(msg.chat.id, "You can use Admin Tools now")
            else:
                self.bot.send_message(msg.chat.id, "Wrong password")

        @self.bot.message_handler(commands=["force_stop"])
        def dm_at_force_stop(msg):
            if not check_auth(self, msg.from_user.id):
                return
            try:
                kill(getpid(), 2)
            except Exception as e:
                self.bot.send_message(msg.chat.id, str(e))
            self.bot.send_message(msg.chat.id, "Cannot terminate process")

        @self.bot.message_handler(commands=["post"])
        def dm_at_post(msg):
            if not check_auth(self, msg.from_user.id):
                return
            with open(self.udb_path) as udb:
                users = json.load(udb)['users']
            for usr in users:
                self.bot.send_message(usr, msg.text[6:])

        @self.bot.message_handler(commands=["quit_AT"])
        def dm_at_quit_at(msg):
            if not check_auth(self, msg.from_user.id):
                return
            new_auth(self, msg.from_user.id, True)
            self.bot.send_message(msg.from_user.id, "AT Session closed")


#-- JSON-BASED LOADER --#
if __name__ == "__main__":
    with open("boot_data.json") as bd:
        boot_data = json.load(bd)
    bot = Bot(boot_data["api_token"])
    bot.load_handlers()
    if "admin_tools" in boot_data and boot_data["admin_tools"]["accessible"]:
        bot.enable_admin_tools(boot_data["admin_tools"]["password"])
    bot.boot()