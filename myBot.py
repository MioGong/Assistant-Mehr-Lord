import telebot
import random
from datetime import datetime
from openai import OpenAI
import json
import threading
import pyttsx3
import os
import requests
from bs4 import BeautifulSoup
import yt_dlp
from telebot import types
import re
# -------------------------
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

bot = telebot.TeleBot(TOKEN)
tts_engine = pyttsx3.init()

# تنظیم بهترین حالت برای فارسی
tts_engine.setProperty('rate', 120)
tts_engine.setProperty('volume', 1.0)
tts_engine.setProperty('pitch', 50)

voices = tts_engine.getProperty('voices')
for v in voices:
    if "fa" in v.id.lower() or "en" in v.name.lower():
        tts_engine.setProperty('voice', v.id)
        break
# -------------------------
#   LOAD BANNED WORDS
# -------------------------
banned_words = []

if os.path.exists("banned_words.json"):
    try:
        with open("banned_words.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            banned_words = data.get("banned", [])
    except:
        banned_words = []
# -------------------------
#   LOAD MODERATION SETTINGS
# -------------------------
moderation = {
    "anti_link": True,
    "anti_badword": True
}

if os.path.exists("moderation.json"):
    try:
        with open("moderation.json", "r", encoding="utf-8") as f:
            moderation.update(json.load(f))
    except:
        pass

def save_moderation():
    with open("moderation.json", "w", encoding="utf-8") as f:
        json.dump(moderation, f, ensure_ascii=False, indent=4)

COMMAND_DESCRIPTIONS = {
    "start": "سلام و معرفی ربات",
    "info": "درباره ربات",
    "help": "کامند های قابل استفاده",
    "date": "تاریخ امروز",
    "question": "سوال رندوم",
    "userinfo": "اطلاعات کاربر",
    "settitle": "تنظیم لقب",
    "ai": "سوال از AI",
    "remind": "یادآوری",
    "voice": "متن به صدا",
    "kick": "کیک کردن کاربر",
    "weather": "آب و هوا",
    "groupinfo": "اطلاعات گروه",
    "price": "قیمت‌ها",
    "setbirthday": "ثبت تاریخ تولد",
    "birthdays": "لیست تولدهای گروه",
    "addtask" : "اضافه کردن تسک",
    "tasks" : "لیست تسک ها",
    "done" : "اتمام تسک",
    "deltask" : "حذف تسک",
    "cleartasks" : "حذف تمام تسک ها",
    "edittask" : "ویرایش تسک",
    "download" : "دانلود کلیپ از اینستا",
    "font" : " ادیت متن با فونت درخواستی",
    "antilink": "ضد لینک ",
    "antibadword" : "ضد فحش"

}

# -------------------------
#    OPENROUTER CLIENT
# -------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# -------------------------
#    LOAD QUESTIONS
# -------------------------
with open("questions.txt", "r", encoding="utf-8") as f:
    questions = [line.strip() for line in f if line.strip()]

used_questions = []
last_seen = {}

# -------------------------
#    LOAD AUTO REPLIES
# -------------------------
with open("auto_replies.json", "r", encoding="utf-8") as f:
    auto_replies = json.load(f)

# -------------------------
#    LOAD BIRTHDAYS (SAFE)
# -------------------------
birthdays = {}

if os.path.exists("birthdays.json"):
    try:
        with open("birthdays.json", "r", encoding="utf-8") as f:
            data = f.read().strip()
            if data:
                birthdays = json.loads(data)
            else:
                birthdays = {}
    except:
        birthdays = {}
else:
    birthdays = {}

def save_birthdays():
    with open("birthdays.json", "w", encoding="utf-8") as f:
        json.dump(birthdays, f, ensure_ascii=False, indent=4)


def contains_banned_word(text):
    text = clean_text(text)
    for word in banned_words:
        word_clean = clean_text(word)
        if word_clean and word_clean in text:
            return True
    return False
@bot.message_handler(commands=['antilink'])
def set_antilink(message):
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت: /antilink on یا /antilink off")

    action = parts[1].lower()
    if action not in ["on", "off"]:
        return bot.reply_to(message, "فرمت درست: /antilink on یا /antilink off")

    moderation["anti_link"] = True if action == "on" else False
    save_moderation()

    bot.reply_to(message, f"🔗 آنتی لینک {'روشن ✅' if moderation['anti_link'] else 'خاموش ❌'}")

@bot.message_handler(commands=['antibadword'])
def set_antibadword(message):
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت: /antibadword on یا /antibadword off")

    action = parts[1].lower()
    if action not in ["on", "off"]:
        return bot.reply_to(message, "فرمت درست: /antibadword on یا /antibadword off")

    moderation["anti_badword"] = True if action == "on" else False
    save_moderation()

    bot.reply_to(
        message,
        f"🤬 فیلتر فحش {'روشن ✅' if moderation['anti_badword'] else 'خاموش ❌'}"
    )


# -------------------------
#       COMMANDS
# -------------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "سلام! ربات سوال‌سنج آماده‌ست 😎\nبرای گرفتن سوال: /question")

@bot.message_handler(commands=['help'])
def show_commands(message):
    cmds = get_all_commands()
    text = "🧾 لیست دستورات ربات:\n\n"
    for c in cmds:
        desc = COMMAND_DESCRIPTIONS.get(c, "بدون توضیح")
        text += f"/{c} - {desc}\n"
    bot.reply_to(message, text)

def get_all_commands():
    cmds = []
    for handler in bot.message_handlers:
        filters = handler.get("filters", {})
        if "commands" in filters:
            cmds.extend(filters["commands"])
    return cmds

@bot.message_handler(commands=['info'])
def info(message):
    bot.reply_to(message,
                 "سلام! من یه ربات ساخته‌شده توسط مهرزاد عزیزم 😎❤️")

@bot.message_handler(commands=['pair'])
def pair(message):
    try:
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(
                message,
                "❤️ آیدی شخص مهم مهرزاد رو بفرست.\n\nمثال:\n/pair @ID"
            )
            return

        username = args[1]

        if username.lower() == "@zees_ha":
            bot.reply_to(
                message,
                "❤️ مهرزاد تو رو خیلی دوست داره ❤️"
            )
        else:
            bot.reply_to(
                message,
                "❌ این شخص مهم مهرزاد نیست."
            )

    except Exception as e:
        bot.reply_to(message, f"خطا: {e}")

@bot.message_handler(commands=['date'])
def send_date(message):
    today = datetime.now().strftime("%Y/%m/%d")
    bot.reply_to(message, f"امروز: {today} 📅")

@bot.message_handler(commands=['question'])
def question(message):
    q = random.choice(questions)
    bot.reply_to(message, q)

# -------------------------
#     SET BIRTHDAY
# -------------------------
@bot.message_handler(commands=['setbirthday'])
def set_birthday(message):
    try:
        text = message.text.replace("/setbirthday", "").strip()

        if "-" not in text:
            bot.reply_to(message, "فرمت درست نیست!\nمثال:\n/setbirthday علی - 1383/05/22")
            return

        name, date = text.split("-", 1)
        name = name.strip()
        date = date.strip()

        chat_id = str(message.chat.id)

        if chat_id not in birthdays:
            birthdays[chat_id] = []

        birthdays[chat_id].append({
            "name": name,
            "date": date
        })

        save_birthdays()

        bot.reply_to(message, f"تولد {name} با تاریخ {date} ذخیره شد 🎉")

    except Exception as e:
        bot.reply_to(message, f"خطا رخ داد: {e}")

# -------------------------
#     LIST BIRTHDAYS
# -------------------------
@bot.message_handler(commands=['birthdays'])
def list_birthdays(message):
    chat_id = str(message.chat.id)

    if chat_id not in birthdays or len(birthdays[chat_id]) == 0:
        bot.reply_to(message, "هیچ تولدی ثبت نشده 🙂")
        return

    text = "🎂 لیست تولدهای گروه:\n\n"
    for item in birthdays[chat_id]:
        text += f"👤 {item['name']}\n📅 {item['date']}\n\n"

    bot.reply_to(message, text)


@bot.message_handler(commands=['userinfo'])
def userinfo(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "فرمت: /userinfo @username یا /userinfo user_id")
        return

    identifier = parts[1]

    try:
        # گرفتن آیدی کاربر
        if identifier.startswith("@"):
            username = identifier[1:]
            user_id = None
            # بررسی اعضایی که last_seen دارن
            for uid, data in last_seen.items():
                if data.get("username") == username:
                    user_id = uid
                    break
            if not user_id:
                # اگر کسی با این username هنوز پیام نداده، تلاش برای گرفتن از گروه
                found = False
                for member in bot.get_chat_administrators(message.chat.id):
                    if member.user.username == username:
                        user_id = member.user.id
                        found = True
                        break
                if not found:
                    bot.reply_to(message, "کاربر پیدا نشد 😅")
                    return
        else:
            user_id = int(identifier)

        # گرفتن اطلاعات کاربر
        member = bot.get_chat_member(message.chat.id, user_id)
        user = member.user

        info_lines = [
            f"🆔 ID: {user.id}",
            f"👤 Username: @{user.username}" if user.username else "👤 Username: ندارد",
            f"📛 First name: {user.first_name}" if user.first_name else "📛 First name: ندارد",
            f"📛 Last name: {user.last_name}" if user.last_name else "📛 Last name: ندارد",
            f"🛡 Status in group: {member.status}",
        ]

        # تاریخ آخرین فعالیت
        if user_id in last_seen:
            last_time = last_seen[user_id]["time"].strftime("%Y/%m/%d - %H:%M:%S")
            info_lines.append(f"⏰ Last seen: {last_time}")
        else:
            info_lines.append("⏰ Last seen: ❌")

        # تعداد پیام‌ها، فایل‌ها و لینک‌ها (اگر ذخیره‌سازی داری)
        if "message_count" in last_seen.get(user_id, {}):
            msg_count = last_seen[user_id]["message_count"]
            info_lines.append(f"💬 تعداد پیام‌ها: {msg_count}")
        else:
            info_lines.append("💬 تعداد پیام‌ها: ❌ نامعلوم")

        if "files_sent" in last_seen.get(user_id, {}):
            files_count = last_seen[user_id]["files_sent"]
            info_lines.append(f"📎 تعداد فایل‌ها: {files_count}")
        else:
            info_lines.append("📎 تعداد فایل‌ها: ❌ نامعلوم")

        if "links_sent" in last_seen.get(user_id, {}):
            links_count = last_seen[user_id]["links_sent"]
            info_lines.append(f"🔗 تعداد لینک‌ها: {links_count}")
        else:
            info_lines.append("🔗 تعداد لینک‌ها: ❌ نامعلوم")

        # تاریخ عضویت (در صورت موجود)
        if hasattr(member, "until_date") and member.until_date:
            join_date = member.until_date.strftime("%Y/%m/%d")
            info_lines.append(f"📅 Joined date: {join_date}")

        bot.reply_to(message, "\n".join(info_lines))

    except Exception as e:
        bot.reply_to(message, f"خطا در پیدا کردن اطلاعات کاربر 😅\n{str(e)}")


@bot.message_handler(commands=['settitle'])
def set_title(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "فرمت: /settitle @username لقب_جدید")
        return

    identifier = parts[1]
    new_title = parts[2]

    try:
        # پیدا کردن user_id
        if identifier.startswith("@"):
            username = identifier[1:]
            user_id = None
            for uid, data in last_seen.items():
                if data.get("username") == username:
                    user_id = uid
                    break
            if not user_id:
                bot.reply_to(message,
                             "کاربر پیدا نشد یا هنوز با بات تعامل نداشته 😅")
                return
        else:
            user_id = int(identifier)

        # تغییر لقب (custom title)
        bot.set_chat_administrator_custom_title(chat_id=message.chat.id,
                                                user_id=user_id,
                                                custom_title=new_title)

        bot.reply_to(
            message,
            f"لقب @{identifier} با موفقیت به «{new_title}» تغییر کرد ✅")

    except Exception as e:
        bot.reply_to(message, f"خطا در تغییر لقب 😅\n{str(e)}")


def parse_time(timestr):
    """ دریافت رشته زمان مثل 1:02:20 و تبدیل به ثانیه """
    parts = timestr.split(":")
    parts = [int(p) for p in parts]

    # پشتیبانی از فرمت های:
    # SS
    # MM:SS
    # HH:MM:SS
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        return None


@bot.message_handler(commands=['remind'])
def remind(message):
    try:
        parts = message.text.split(maxsplit=2)

        # parts = ['/remind', '00:10:00', 'توضیح کامل']
        if len(parts) < 3:
            return bot.reply_to(message, "فرمت درست:\n/remind HH:MM:SS توضیح")

        time_str = parts[1]  # زمان
        text = parts[2]  # توضیح کامل

        seconds = parse_time(time_str)
        if seconds is None:
            return bot.reply_to(
                message,
                "⛔ فرمت زمان اشتباهه!\nمثال درست:\n/remind 01:02:20 یه کاری بکن"
            )

        bot.reply_to(message, f"باشه! {time_str} دیگه یادت میندازم 😉")

        threading.Timer(
            seconds, lambda: bot.send_message(message.chat.id,
                                              f"⏰ یادآوری:\n{text}")).start()

    except Exception as e:
        bot.reply_to(message, f"یه مشکلی خوردیم 😅\n{str(e)}")


@bot.message_handler(commands=['voice'])
def voice_command(message):
    parts = message.text.split(" ", 1)

    if len(parts) < 2:
        return bot.reply_to(message, "فرمت درست:\n/voice متن دلخواه")

    text = parts[1]

    try:
        filename = f"voice_{message.chat.id}.mp3"

        tts_engine.save_to_file(text, filename)
        tts_engine.runAndWait()

        with open(filename, 'rb') as f:
            bot.send_voice(message.chat.id, f)

        os.remove(filename)

    except Exception as e:
        bot.reply_to(message, f"مشکل پیش اومد 😅\n{str(e)}")


# -------------------------
#      AI COMMAND (OpenRouter)
# -------------------------
@bot.message_handler(commands=['ai'])
def ai_command(message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ai your question...")
        return

    user_prompt = parts[1]
    try:
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct",
            messages=[{
                "role": "user",
                "content": user_prompt
            }])
        ai_text = response.choices[0].message.content
        bot.reply_to(message, ai_text)
    except Exception as e:
        bot.reply_to(message, f"خطا در اتصال به OpenRouter 😢\n{str(e)}")


@bot.message_handler(commands=['kick'])
def kick_user(message):
    parts = message.text.split()

    if len(parts) < 2:
        return bot.reply_to(message, "فرمت درست:\n/kick @username")

    identifier = parts[1]

    # باید @ داشته باشه
    if not identifier.startswith("@"):
        return bot.reply_to(message, "حتماً باید @username بدی 😅")

    username = identifier[1:]

    try:
        # تلاش برای پیدا کردن کاربر از گروه (تلگرام خودش user_id رو میده)
        members = bot.get_chat_administrators(message.chat.id)
        user_id = None

        # روش ۱: چک بین ادمین‌ها (چون تلگرام با username راحت پیدا می‌کنه)
        for m in members:
            if m.user.username and m.user.username.lower() == username.lower():
                user_id = m.user.id
                break

        # روش ۲: اگر بین ادمین‌ها نبود، بزن get_chat_member با username
        if user_id is None:
            try:
                member = bot.get_chat_member(message.chat.id, username)
                user_id = member.user.id
            except:
                pass

        if user_id is None:
            return bot.reply_to(message,
                                "کاربر پیدا نشد 😅 ممکنه تو گروه نباشه.")

        # کیک (نه بن!)
        bot.kick_chat_member(message.chat.id, user_id)
        bot.unban_chat_member(message.chat.id,
                              user_id)  # تا بشه دوباره جوین بدهد

        bot.reply_to(message, f"🚪 کاربر @{username} از گروه خارج شد.")

    except Exception as e:
        bot.reply_to(message, f"نشد کیکش کنم 😅\n{str(e)}")


@bot.message_handler(commands=['weather'])
def weather_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت: /weather <نام شهر>")
    city = parts[1].strip()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={API_KEY}&lang=fa"
    try:
        res = requests.get(url).json()
        if res.get("cod") != 200:
            return bot.reply_to(message, "شهر پیدا نشد 😅")
        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        bot.reply_to(message, f"دمای فعلی {city}: {temp}°C 🌤\nوضعیت: {desc}")
    except Exception as e:
        bot.reply_to(message, f"خطا در دریافت وضعیت هوا 😢\n{e}")


@bot.message_handler(commands=['groupinfo'])
def group_info(message):
    try:
        chat = bot.get_chat(message.chat.id)
        members_count = bot.get_chat_members_count(message.chat.id)
        admins = bot.get_chat_administrators(message.chat.id)

        # جدا کردن ادمین‌ها و ربات‌ها
        admin_list = []
        bot_count = 0
        for a in admins:
            if a.user.is_bot:
                bot_count += 1
            else:
                username = a.user.username if a.user.username else a.user.first_name
                admin_list.append(f"{username} ({a.status})")

        normal_members_count = members_count - len(admin_list) - bot_count

        # نوع گروه
        group_type = "سوپرگروه" if chat.type == "supergroup" else chat.type

        # وضعیت گروه (عمومی / خصوصی) و لینک
        try:
            invite_link = chat.invite_link
            group_privacy = "عمومی" if invite_link else "خصوصی"
            link_text = invite_link if invite_link else "❌ ندارد"
        except:
            group_privacy = "خصوصی"
            link_text = "❌ ندارد"

        # آخرین پیام
        last_msg_info = "نامعلوم"
        if hasattr(chat, 'last_message') and chat.last_message:
            sender = chat.last_message.from_user
            sender_name = sender.username if sender.username else sender.first_name
            last_msg_info = f"ID: {chat.last_message.message_id} | فرستنده: {sender_name}"

        # اعضای فعال اخیر
        recent_active = []
        for user_id, data in last_seen.items():
            if message.chat.id == chat.id:
                time_str = data["time"].strftime("%Y/%m/%d - %H:%M:%S")
                uname = data["username"] if data["username"] else "نامعلوم"
                recent_active.append(f"{uname}: {time_str}")
        recent_active_text = "\n".join(recent_active[:10]) if recent_active else "❌ هیچکدام"

        text = f"""
📌 اطلاعات گروه:

نام گروه: {chat.title}
آیدی گروه: {chat.id}
نوع گروه: {group_type}
وضعیت گروه: {group_privacy}
لینک گروه: {link_text}

تعداد کل اعضا: {members_count}
تعداد اعضای عادی: {normal_members_count}
تعداد ادمین‌ها: {len(admin_list)}
ادمین‌ها: {', '.join(admin_list) if admin_list else '❌ ندارد'}
تعداد ربات‌ها: {bot_count}

آخرین پیام گروه: {last_msg_info}

اعضای فعال اخیر:
{recent_active_text}
"""
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"مشکل در دریافت اطلاعات گروه 😅\n{e}")

@bot.message_handler(commands=['price'])
def get_prices(message):
    import requests

    API_KEY = "freeEPMJw4l0kNhXU3wJiVwDMpoRqmYm"

    try:
        url = f"https://api.navasan.tech/latest/?api_key={API_KEY}"
        res = requests.get(url)
        
        # چک کردن وضعیت پاسخ
        if res.status_code != 200:
            bot.reply_to(message, f"خطا در دریافت داده‌ها 😅\nکد وضعیت: {res.status_code}")
            return
        
        data = res.json()
        print(data)  # برای دیباگ، ببین کلیدها چطوری هستن

        # گرفتن مقادیر با کلیدهای محتمل
        dollar = data.get("usd") or data.get("USD") or "نامعلوم"
        euro = data.get("eur") or data.get("EUR") or "نامعلوم"
        gold18 = data.get("geram18") or data.get("gold18") or "نامعلوم"
        sekke = data.get("sekke") or "نامعلوم"
        nim = data.get("nim") or "نامعلوم"

        # فرمت کردن اعداد اگر عدد باشن
        def fmt(x):
            return f"{x:,}" if isinstance(x, (int, float)) else x

        text = f"""
💰 **آخرین قیمت‌های بازار ایران**

💵 دلار: {fmt(dollar)} تومان
💶 یورو: {fmt(euro)} تومان

🥇 طلا ۱۸ عیار: {fmt(gold18)} تومان

🟡 سکه بهار آزادی: {fmt(sekke)} تومان
🟢 نیم سکه: {fmt(nim)} تومان

⏳ آپدیت لحظه‌ای از Navasan
"""
        bot.reply_to(message, text, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"متاسفانه نتونستم قیمت‌ها رو بگیرم 😅\n{e}")


# -------------------------
#   LOAD TASKS
# -------------------------
tasks = []

if os.path.exists("tasks.json"):
    try:
        with open("tasks.json", "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except:
        tasks = []
else:
    tasks = []

def save_tasks():
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)


@bot.message_handler(commands=['addtask'])
def add_task(message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت درست:\n/addtask متن کار")

    task_text = parts[1].strip()

    tasks.append({
        "text": task_text,
        "done": False
    })
    save_tasks()

    bot.reply_to(message, f"✔️ کار جدید اضافه شد:\n{task_text}")

@bot.message_handler(commands=['tasks'])
def list_tasks(message):
    if not tasks:
        return bot.reply_to(message, "هیچ کاری ثبت نشده 😎")

    text = "📝 لیست کارها:\n\n"
    for i, t in enumerate(tasks, start=1):
        status = "✔️" if t["done"] else "❌"
        text += f"{i}. {t['text']} — {status}\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=['done'])
def mark_done(message):
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت: /done شماره")

    try:
        index = int(parts[1]) - 1
        if index < 0 or index >= len(tasks):
            return bot.reply_to(message, "این شماره وجود نداره 😅")

        tasks[index]["done"] = True
        save_tasks()

        bot.reply_to(message, f"✅ انجام شد:\n{tasks[index]['text']}")

    except:
        bot.reply_to(message, "شماره درست نیست 😁")

@bot.message_handler(commands=['edittask'])
def edit_task(message):
    parts = message.text.split(" ", 2)

    # باید حداقل 3 بخش داشته باشه → کامند / شماره / متن جدید
    if len(parts) < 3:
        return bot.reply_to(message, "فرمت درست:\n/edittask شماره متن جدید")

    try:
        index = int(parts[1]) - 1
        new_text = parts[2].strip()

        if index < 0 or index >= len(tasks):
            return bot.reply_to(message, "این شماره وجود نداره 😅")

        old_text = tasks[index]["text"]
        tasks[index]["text"] = new_text
        save_tasks()

        bot.reply_to(
            message,
            f"✏️ تسک شماره {index+1} ویرایش شد:\n\n"
            f"🔸 قدیم: {old_text}\n"
            f"🔹 جدید: {new_text}"
        )

    except:
        bot.reply_to(message, "شماره رو درست بده رفیق 😎")


@bot.message_handler(commands=['deltask'])
def delete_task(message):
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "فرمت: /deltask شماره")

    try:
        index = int(parts[1]) - 1
        if index < 0 or index >= len(tasks):
            return bot.reply_to(message, "این شماره نیست 😅")

        removed = tasks.pop(index)
        save_tasks()

        bot.reply_to(message, f"🗑 حذف شد:\n{removed['text']}")

    except:
        bot.reply_to(message, "شماره رو درست بده رفیق 😎")


@bot.message_handler(commands=['cleartasks'])
def clear_tasks(message):
    global tasks
    
    if not tasks:
        return bot.reply_to(message, "هیچ کاری وجود نداره که پاکش کنم 😎")

    tasks = []  # خالی کردن تمام لیست
    save_tasks()  # ذخیره تغییرات

    bot.reply_to(message, "🗑 کل تسک‌ها با موفقیت پاک شدن!")


@bot.message_handler(commands=['download'])
def download_handler(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(
            message,
            "لینک ویدیو رو بده رفیق 😉\nمثال:\n/download https://www.instagram.com/reel/xxxx\n/download https://youtu.be/xxxx"
        )

    url = parts[1].strip()
    bot.reply_to(message, "⏳ دارم ویدیو رو شکار می‌کنم...")

    # تنظیمات yt-dlp
    ydl_opts = {
    'outtmpl': f"dl_{message.message_id}.%(ext)s",
    'format': 'best[ext=mp4]/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'merge_output_format': 'mp4',
    'cookiefile': 'cookies.txt'
}

    try:
        # دانلود
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                filename = f"dl_{message.message_id}.mp4"

            if not os.path.exists(filename):
                return bot.reply_to(message, "فایل دانلود نشد 😕")

            size = os.path.getsize(filename)
            max_allowed = 49 * 1024 * 1024

            # ارسال
            with open(filename, 'rb') as f:
                if size <= max_allowed:
                    try:
                        bot.send_video(message.chat.id, f)
                    except:
                        f.seek(0)
                        bot.send_document(message.chat.id, f)
                else:
                    return bot.reply_to(
                        message,
                        f"فایل دانلود شد ولی {size/1024/1024:.1f}MB هست و تلگرام اجازه ارسالش نمی‌ده."
                    )

        # پاک کردن فایل
        os.remove(filename)

    except Exception as e:
        return bot.reply_to(message, f"خطایی خوردیم داداش: {str(e)}")
    

@bot.message_handler(commands=['font'])
def font_command(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "یه متنی بده تبدیل کنم برات 😎\nمثال:\n/font salam")

    text = parts[1]

    fonts = {
        "Bold": str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
            "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
        ),
        "Italic": str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻"
            "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
        ),
        "Cursive": str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏"
            "𝒜𝐵𝒞𝒟𝐸𝐹𝐺𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
        ),
        "Bubble": str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩"
            "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩"
        ),
        "Square": str.maketrans(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
            "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
        ),
        "SmallCaps": str.maketrans(
            "abcdefghijklmnopqrstuvwxyz",
            "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
        )
    }

    output = "🔥 فونتای خفن آماده شد:\n\n"
    for name, table in fonts.items():
        try:
            converted = text.translate(table)
            output += f"**{name}:**\n{converted}\n\n"
        except:
            pass

    bot.reply_to(message, output, parse_mode="Markdown")

# -------------------------
#   RANDOM QUESTION LOGIC
# -------------------------
def send_random_question(message):
    global used_questions
    if len(used_questions) == len(questions):
        used_questions = []

    available = [q for q in questions if q not in used_questions]
    q = random.choice(available)
    used_questions.append(q)
    bot.reply_to(message, q)


# -------------------------
#   HANDLE TEXT
# -------------------------
def clean_text(text):
    # حذف ایموجی و علائم، یکدست‌سازی متن
    text = text.lower().strip()
    text = re.sub(r'[^\w\sآ-ی]', '', text)
    return text

@bot.message_handler(func=lambda message: True)
def handle_all(message):

    # -------- ثبت آخرین فعالیت --------
    last_seen[message.from_user.id] = {
        "username": message.from_user.username,
        "time": datetime.now()
    }

    if not message.text:
        return

    raw_text = message.text
    text = clean_text(raw_text)

    # -------- ANTI LINK --------
    if moderation.get("anti_link", True):
        try:
            if ("http://" in raw_text or "https://" in raw_text or "t.me/" in raw_text):

                bot.delete_message(message.chat.id, message.message_id)

                warn_user = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else message.from_user.first_name
                )

                bot.send_message(
                    message.chat.id,
                    f"🚫 {warn_user}\nلینک نفرست کصکش❌"
                )
                return
        except:
            pass
    # ---------------------------

    # -------- BANNED WORD FILTER --------
    if moderation.get("anti_badword", True):
        try:
            if contains_banned_word(raw_text):

                bot.delete_message(message.chat.id, message.message_id)

                warn_user = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else message.from_user.first_name
                )

                bot.send_message(
                    message.chat.id,
                    f"⚠️ {warn_user}\nحرفت مناسب نبود ❌"
                )
                return
        except:
            pass
    # ----------------------------------

    # -------- AUTO REPLY --------
    for reply, triggers in auto_replies.items():
        for trigger in triggers:
            if clean_text(trigger) in text:
                return bot.reply_to(message, reply)
    # ---------------------------

    # -------- RANDOM QUESTION --------
    if text == "سوال":
        return send_random_question(message)

    if text.startswith("سوال "):
        try:
            index = int(text.split()[1]) - 1
            if 0 <= index < len(questions):
                return bot.reply_to(message, questions[index])
            return bot.reply_to(message, "این شماره سوال وجود نداره 😅")
        except:
            return bot.reply_to(message, "فرمت درست: سوال 5")
    # --------------------------------

# -------------------------
bot.polling()
