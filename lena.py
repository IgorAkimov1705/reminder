import telebot
import sqlite3
import datetime
import time
import pytz
import threading
import re
from telebot import types


conn = sqlite3.connect('reminders.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT, subject TEXT, text TEXT, day_of_week TEXT, time TEXT)''')
conn.commit()

bot = telebot.TeleBot("6593162871:AAESlX79lDCt1MR-hv7hMDdy51RdRFVBSlg")

global krasnoyarsk_tz, moscow_tz
krasnoyarsk_tz = pytz.timezone('Asia/Krasnoyarsk')
moscow_tz = pytz.timezone('Europe/Moscow')

allowed_user_ids = [1233556774, 5203157663, 1690689969, 6631818240]  # список chat_id 

@bot.message_handler(commands=['doc'], func=lambda message: message.chat.id in allowed_user_ids)
def doc(message): 
    bot.send_document(message.chat.id, open('Документация.docx', 'rb'))

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"Привет! Я бот-Напоминалка.\nЯ идеально подойду если ты не следишь за времиен при подготовке к ОГЭ/ЕГЭ \nИспользуй команду /com чтобы узнать все команды.")
       
@bot.message_handler(commands=['com'])
def start(message):
    bot.send_message(message.chat.id, f"Привет! \n/add - добавить напоминание\n/del - удалить напоминание\n/reminders - узнать все напоминания\n/help - связаться с тех поддержкой")   
       
@bot.message_handler(commands=['help'])
def start(message):
    bot.send_message(message.chat.id, f"Привет! \nСвязаться с автором - @GAsFJK\nСвязаться с кодером - @AIJEUX")  

@bot.message_handler(commands=['add'])
def add_reminder(message):
    bot.send_message(message.chat.id, "Выбери категорию напоминания:", reply_markup=generate_category_keyboard())
    bot.register_next_step_handler(message, add_subject_or_text)

def add_subject_or_text(message):
    category = message.text
    if category == "Консультация":
        bot.send_message(message.chat.id, "Напиши название предмета:")
        bot.register_next_step_handler(message, add_time, category)
    elif category == "ДРУГОЕ":
        bot.send_message(message.chat.id, "О чем тебе напоминать?")
        bot.register_next_step_handler(message, add_time, category)  
    elif category == "Перерыв":
        bot.send_message(message.chat.id, "О чем тебе напоминать?")
        bot.register_next_step_handler(message, add_time, category)

def add_time(message, category):
    if category == "Консультация":
        subject = message.text
        text = None
    elif category == "ДРУГОЕ":
        subject = None
        text = message.text
    elif category == "Перерыв":
        subject = None
        text = message.text
    bot.send_message(message.chat.id, "Выбери день недели:", reply_markup=generate_day_of_week_keyboard())
    bot.register_next_step_handler(message, save_reminder, category, subject, text)

def save_reminder(message, category, subject, text):
    day_of_week = message.text
    if message.text.lower() in ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]:
        bot.send_message(message.chat.id, "Введи время в формате Часы:Минуты (например, 09:30):")
        bot.register_next_step_handler(message, save_time, category, subject, text, day_of_week)
    else:
        bot.send_message(message.chat.id, "Такого дня недели нет. Попробуй еще раз.", reply_markup=generate_day_of_week_keyboard())
        bot.register_next_step_handler(message, save_reminder, category, subject, text)

def save_time(message, category, subject, text, day_of_week):
    time = message.text
    user_id = message.from_user.id
    if re.match(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$', message.text):
        cursor.execute("INSERT INTO reminders (user_id, category, subject, text, day_of_week, time) VALUES (?, ?, ?, ?, ?, ?)", (user_id, category, subject, text, day_of_week, time))
        conn.commit()
        bot.send_message(message.chat.id, "Напоминание успешно добавлено!") 
    else:
        bot.send_message(message.chat.id, "Некорректное время. Введи время в формате Часы:Минуты (например, 09:30):")
        bot.register_next_step_handler(message, save_time, category, subject, text, day_of_week)

def generate_category_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Консультация'))
    keyboard.add(types.KeyboardButton('Перерыв'))
    keyboard.add(types.KeyboardButton('ДРУГОЕ'))
    return keyboard

def generate_day_of_week_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Понедельник'))
    keyboard.add(types.KeyboardButton('Вторник'))
    keyboard.add(types.KeyboardButton('Среда'))
    keyboard.add(types.KeyboardButton('Четверг'))
    keyboard.add(types.KeyboardButton('Пятница'))
    keyboard.add(types.KeyboardButton('Суббота'))
    keyboard.add(types.KeyboardButton('Воскресенье'))
    return keyboard    

@bot.message_handler(commands=['del'])
def del_reminder(message):
    cursor.execute("SELECT id, category, subject, text FROM reminders WHERE user_id=?", (message.from_user.id,))
    reminders = cursor.fetchall()
    keyboard = types.InlineKeyboardMarkup()
    for reminder in reminders:
        if reminder[2]:
            button_text = f"{reminder[1]} - {reminder[2]}"
        else:
            button_text = f"{reminder[1]} - {reminder[3]}"
        button = types.InlineKeyboardButton(text=button_text, callback_data=reminder[0])
        keyboard.add(button)
    if keyboard:
        bot.send_message(message.chat.id, "Выбери напоминание, которое надо удалить:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "У тебя пока нет сохраненных напоминаний.")\
            
@bot.callback_query_handler(func=lambda call: True)
def delete_reminder(call):
    cursor.execute("DELETE FROM reminders WHERE id=?", (call.data,))
    conn.commit()
    bot.send_message(call.message.chat.id, "Напоминание успешно удалено!")    
    
@bot.message_handler(commands=['reminders'])
def list_reminders(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM reminders WHERE user_id=?", (user_id,))
    reminders = cursor.fetchall()
    response_text = "Ваши напоминания:\n"
    for reminder in reminders:
        if reminder[4] == None:
            response_text += reminder[2] + ": " + reminder[3] +" Когда: " + reminder[5] +" " + reminder[6] + "\n"
        else:
            response_text += reminder[2] + ": " + reminder[4] +" Когда: " + reminder[5] +" " + reminder[6] + "\n"

    bot.send_message(message.chat.id, response_text)
    check_reminders(message)

def check_reminders(message): 
    day_mapping = {
    "monday": "понедельник",
    "tuesday": "вторник",
    "wednesday": "среда",
    "thursday": "четверг",
    "friday": "пятница",
    "saturday": "суббота",
    "sunday": "воскресенье"
    }
    
    current_day_of_week = datetime.datetime.now(krasnoyarsk_tz).strftime('%A').lower()
    russian_day_of_week = day_mapping.get(current_day_of_week, "нет данных")
    current_time = datetime.datetime.now(krasnoyarsk_tz).strftime('%H:%M')
    current_time_30min = (datetime.datetime.now(krasnoyarsk_tz) + datetime.timedelta(minutes=30)).strftime('%H:%M')
    current_time_60min = (datetime.datetime.now(krasnoyarsk_tz) + datetime.timedelta(hours=1)).strftime('%H:%M')

    print('True')
    
    cursor.execute("SELECT * FROM reminders")
    reminders = cursor.fetchall()
    for reminder in reminders:
        if reminder[5].lower() == russian_day_of_week:
            if reminder[6] == current_time_60min:
                if reminder[4] == None:
                    bot.send_message(reminder[1], f"Напоминаю, через 1 час у вас: {reminder[2]}\nПредмет: {reminder[3]}\nВремя: {reminder[6]}")
                else:
                    bot.send_message(reminder[1], f"Напоминаю: {reminder[4]} в {reminder[6]}")
            elif reminder[6] == current_time_30min:
                if reminder[4] == None:
                    bot.send_message(reminder[1], f"Напоминаю, через 30 минут у вас: {reminder[2]}\nПредмет: {reminder[3]}\nВремя: {reminder[6]}")
                else:
                    bot.send_message(reminder[1], f"Напоминаю: {reminder[4]} в {reminder[6]}")
            elif reminder[6] == current_time:
                if reminder[4] == None:
                    bot.send_message(reminder[1], f"Напоминаю, сейчас у вас: {reminder[2]}\nПредмет: {reminder[3]}\nВремя: {reminder[6]}")
                else:
                    bot.send_message(reminder[1], f"Напоминаю: {reminder[4]} в {reminder[6]}")
                                     
def run_check_reminders():
    while True:
        check_reminders(None)  # Передаем None, так как message не требуется
        time.sleep(60)  # Периодичность проверки в секундах

reminder_thread = threading.Thread(target=run_check_reminders)
reminder_thread.start()


bot.infinity_polling()           