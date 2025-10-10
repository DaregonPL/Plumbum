import telebot
import json
from os.path import exists
from os import kill, getpid
from base64 import b64decode, b64encode


class Bot:
    start_message = """\
Hello! This bot is an emergency base64 converter.
Use /help for user manual"""

    help_message = """\
<b>Commands:</b>
/start - Restart bot
/help - Display user manual (this one)

<i># Special-syntax commands #</i>
/b64 - Encode following text with base64
  Example: <code>/b64 Hewwo :3</code>
/str - Decode following text with base64
  Example: <code>/str SGV3d28gOjM=</code>
<i># Important: the message must start with "/b64" or "/str", text for processing is selected after first space found #</i>
"""

    syntax_error_message = """\
Wrong syntax. Use /help"""

    def __init__(self, api_token):
        self.bot = telebot.TeleBot(api_token)
        self.udb_path = "users_data.json"
        self.commands_functions = {
            "help": {
                "get-text": lambda usr: self.help_message
            }
        }
        if not exists(self.udb_path):
            with open(self.udb_path, 'w') as udf:
                json.dump({"auth": [],
                           "users": []}, udf, indent=2)

    def boot(self):
        print("Booting up...")
        self.bot.infinity_polling()

    def load_handlers(self):
        print("Loading handlers...")

        @self.bot.message_handler(content_types=["photo"])
        def dm_photo(msg):
            photo = max(msg.photo, key=lambda x: x.height)
            self.bot.send_photo(msg.chat.id, photo.file_id)

        @self.bot.message_handler(commands=["start"])
        def dm_start(msg):
            self.bot.send_message(msg.chat.id, self.start_message, parse_mode="html")
            with open(self.udb_path) as udb:
                udb_data = json.load(udb)
                udb_data["users"] = list(set(udb_data["users"] + [msg.from_user.id]))
            with open(self.udb_path, 'w') as udb:
                json.dump(udb_data, udb, indent=2)
        @self.bot.message_handler(commands=["help"])
        def dm_help(msg):
            self.bot.send_message(msg.chat.id, self.commands_functions["help"]["get-text"](msg.chat.id),
                                  parse_mode="html")

        @self.bot.message_handler(commands=["b64"])
        def dm_b64(msg):
            text = msg.text
            if text.startswith("/b64 "):
                user_string = text[5:]
                out = f"<code>{b64encode(user_string.encode()).decode()}</code>"
                self.bot.reply_to(msg, out, parse_mode="html")
            else:
                self.bot.reply_to(msg, self.syntax_error_message, parse_mode="html")

        @self.bot.message_handler(commands=["str"])
        def dm_str(msg):
            text = msg.text
            if text.startswith("/str "):
                user_string = text[5:]
                try:
                    out = f"<code>{b64decode(user_string.encode()).decode()}</code>"
                except Exception as e:
                    out = f"Error: invalid base64 string ({e})"
                self.bot.reply_to(msg, out, parse_mode="html")
            else:
                self.bot.reply_to(msg, self.syntax_error_message, parse_mode="html")

    def enable_admin_tools(self, master_password):
        print("Adding AdminTools:")
        print(" - adding alternative help message...")
        self.master_password = master_password
        self.admin_help_message = """\
<b>Commands:</b>
/start - Restart bot
/help - Display user manual (this one)

<i># Special-syntax commands #</i>
/b64 - Encode following text with base64
  Example: <code>/b64 Hewwo :3</code>
/str - Decode following text with base64
  Example: <code>/str SGV3d28gOjM=</code>
<i># Important: the message must start with "/b64" or "/str", text for processing is selected after first space found #</i>

<i>## Admin Tools ##</i>
/auth {password} - get access to Admin Tools
/post {text} - send every user of this bot a message
/force_stop - stop the bot entirely
/quit_AT - quit admin tools
"""
        self.commands_functions["help"]["get-text"] = lambda usr: self.admin_help_message \
            if check_auth(self, usr) else self.help_message
        print(" - realising session control...")

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
                json.dump(udb_data, udb, indent=2)


        print(" - loading message handlers...")

        @self.bot.message_handler(commands=["auth"])
        def dm_at_auth(msg):
            if msg.text[6:] == self.master_password:
                new_auth(self, msg.from_user.id)
                self.bot.send_message(msg.chat.id, "You can use Admin Tools now")
            else:
                self.bot.send_message(msg.chat.id, "Wrong password")

        @self.bot.message_handler(commands=["force_stop"])
        def dm_at_force_stop(msg):
            if not check_auth(self, msg.from_user.id):
                return
            try:
                kill(getpid(), 9)
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