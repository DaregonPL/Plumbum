from datetime import datetime
import json
from os.path import exists
from os import kill, getpid

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


def timeformat():
    et = datetime.now()
    return (f'{str(et.day).rjust(2, "0")}.{str(et.month).rjust(2, "0")}' +
            f'.{et.year} {et.hour}:{str(et.minute).rjust(2, "0")}')

class Bot:
    start_message = """\
<b>Привет!</b>
Этот бот - место для обмена фотографиями"""
    sign_up_message = """
<b>Для использования неограниченной версии бота необходимо выбрать никнейм.</b>
Можно выбрать один из предложенных вариантов или прислать свой. Никнейм может быть изменён позже"""
    help_message = """\
<b>Команды:</b>
/start - Перезапустить бота
/help - Отобразить список команд (этот)

/profile - Посмотреть свой профиль
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
        if str(user) not in udb_data:
            udb_data['sessions'][str(user)] = {**values}
        else:
            for name, value in values.keys():
                udb_data[str(user)][name] = value
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

    def boot(self):
        print("[STATUS] Pending")
        self.bot.infinity_polling()

    def load_handlers(self):
        print("[STATUS] Loading handlers...")

        @self.bot.message_handler(content_types=["photo"])
        def dm_photo(msg):
            photo = max(msg.photo, key=lambda x: x.height)
            self.bot.send_photo(msg.chat.id, photo.file_id)

        @self.bot.message_handler(commands=["start"])
        def dm_start(msg):
            cid = msg.from_user.id
            users = self.get_users()

            if cid not in users:
                markup = ReplyKeyboardMarkup(resize_keyboard=True)
                buttons = []
                if msg.from_user.username:
                    buttons.append(msg.from_user.username)
                if msg.from_user.first_name:
                    buttons.append(msg.from_user.first_name)
                markup.add(*buttons)

                self.bot.send_message(msg.chat.id, self.start_message, parse_mode="html")
                self.bot.send_message(msg.chat.id, self.sign_up_message, parse_mode="html",
                                      reply_markup=markup)
                self.set_session(cid, expect="nickname")

            else:
                pass

        @self.bot.message_handler(commands=["help"])
        def dm_help(msg):
            self.bot.send_message(msg.chat.id, self.commands_functions["help"]["get-text"](msg.chat.id),
                                  parse_mode="html")

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
                    if msg.text in [user['nickname'] for user in users]:
                        self.bot.send_message(msg.chat.id, self.nick_exists_warning, parse_mode="html")
                        return
                    if cid not in users:
                        users[cid] = {
                            "nickname": msg.text,
                            "created": timeformat()
                        }
                        self.set_session(cid, expect=None)
                        self.set_users(users)
                        self.bot.send_message(msg.chat.id, "ГОЙДА",
                                              reply_markup=telebot.types.ReplyKeyboardRemove())
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