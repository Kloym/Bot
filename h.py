import telebot
from telebot import types
from random import choice
import json
import os
import threading
import time
import schedule
from datetime import datetime, timedelta

token = ''
bot = telebot.TeleBot(token)

RANDOM_TASKS = ['Написать Гвидо письмо', 'Выучить Python', 'Записаться на курс в Нетологию', 'Посмотреть 4 сезон Рик и Морти']
todos_file = 'todos.json'

def load_todos():
    if os.path.exists(todos_file):
        with open(todos_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_todos():
    with open(todos_file, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

todos = load_todos()

HELP = '''
Список доступных команд:
* start - приветствие
* print  - напечатать все задачи на заданную дату
* add - добавить задачу
* random - добавить на сегодня случайную задачу
* help - Напечатать help
* all - Вывод всех задач
* edit - изменение текста задачи
* delete - удаление задачи по порядковому номеру в списке
'''

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!\''
    return ''.join(['\\' + c if c in escape_chars else c for c in text])

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "Привет ✌️",
        reply_markup=main_keyboard()
    )

def parse_date(date_str):
    date_str = date_str.lower()
    if date_str == 'сегодня':
        return datetime.now().strftime('%d.%m.%Y')
    elif date_str == 'завтра':
        return (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
    elif date_str == 'послезавтра':
        return (datetime.now() + timedelta(days=2)).strftime('%d.%m.%Y')
    else:
        try:
            dt = datetime.strptime(date_str, '%d.%m.%Y')
            now = datetime.now()
            if now <= dt <= now + timedelta(days=30):
                return dt.strftime('%d.%m.%Y')
            else:
                return None
        except ValueError:
            return None

last_notify_date = None

def send_daily_notifications():
    global last_notify_date
    today = datetime.now().strftime('%d.%m.%Y')
    if last_notify_date == today:
        return
    print("Время для уведомления!")
    for user_id, user_tasks in todos.items():
        print(f"Проверяю задачи для {user_id}: {user_tasks}")
        tasks_today = user_tasks.get(today, [])
        if tasks_today:
            text = "Ваши задачи на сегодня:\n" + "\n".join(f"- {t}" for t in tasks_today)
            try:
                print(f"Отправляю задачи пользователю {user_id}")
                bot.send_message(int(user_id), text)
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id}: {e}")
    last_notify_date = today

schedule.every().day.at("21:37").do(send_daily_notifications)

def run_scheduler():
    print("Поток уведомлений запущен")
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_scheduler, daemon=True).start()


def add_todo(user_id, date, task):
    user_id = str(user_id)
    parsed_date = parse_date(date)
    if not parsed_date:
        return False
    if user_id not in todos:
        todos[user_id] = {}
    if parsed_date in todos[user_id]:
        todos[user_id][parsed_date].append(task)
    else:
        todos[user_id][parsed_date] = [task]
    save_todos()
    return True


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Старт')
    keyboard.add('Все задачи', 'Добавить', 'Случайная задача')
    keyboard.add('Печать по дате', 'Изменить', 'Удалить')
    keyboard.add('Help')
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я твой todo-бот.", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Help')
def help_button(message):
    bot.send_message(message.chat.id, HELP, reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Случайная задача')
def random_button(message):
    task = choice(RANDOM_TASKS)
    add_todo(message.from_user.id, 'сегодня', task)
    bot.send_message(message.chat.id, f'Задача {escape_markdown(task)} добавлена на сегодня', parse_mode='MarkdownV2', reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Все задачи')
def all_tasks_button(message):
    user_id = str(message.from_user.id)
    if user_id not in todos or not todos[user_id]:
        bot.send_message(message.chat.id, "Нет задач", reply_markup=main_keyboard())
        return
    result = ""
    for date, tasks in todos[user_id].items():
        result += f"*{escape_markdown(str(date)).title()}*\n"
        for i, task in enumerate(tasks, 1):
            result += f"{i}\\. {escape_markdown(str(task))}\n"
        result += "\n"
    bot.send_message(message.chat.id, result.strip(), parse_mode='MarkdownV2', reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Добавить')
def add_button(message):
    msg = bot.send_message(message.chat.id, "Введите дату и задачу через пробел (пример: Завтра Купить хлеб):", reply_markup=main_keyboard())
    bot.register_next_step_handler(msg, add_step)

def add_step(message):
    user_id = message.from_user.id
    try:
        date, task = message.text.split(maxsplit=1)
        if len(task.strip()) < 3:
            bot.send_message(message.chat.id, "Ошибка: задача должна содержать не менее 3 символов.", reply_markup=main_keyboard())
            return
        if not add_todo(user_id, date, task):
            bot.send_message(message.chat.id, "Неверный формат даты. Используйте сегодня, завтра, послезавтра или дд.мм.гггг", reply_markup=main_keyboard())
            return
        bot.send_message(message.chat.id, f'Задача {escape_markdown(task)} добавлена на дату {escape_markdown(date)}', parse_mode='MarkdownV2', reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: дата задача", reply_markup=main_keyboard())
@bot.message_handler(func=lambda message: message.text == 'Печать по дате')
def print_button(message):
    msg = bot.send_message(message.chat.id, "Введите дату:", reply_markup=main_keyboard())
    bot.register_next_step_handler(msg, print_step)

def print_step(message):
    user_id = str(message.from_user.id)
    date = message.text
    parsed_date = parse_date(date)
    if not parsed_date:
        bot.send_message(message.chat.id, "Неверный формат даты. Используйте сегодня, завтра, послезавтра или дд.мм.гггг", reply_markup=main_keyboard())
        return
    if user_id in todos and parsed_date in todos[user_id]:
        tasks = ''
        for task in todos[user_id][parsed_date]:
            tasks += f'[ ] {escape_markdown(task)}\n'
    else:
        tasks = 'Такой даты нет'
    bot.send_message(message.chat.id, tasks, parse_mode='MarkdownV2', reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Изменить')
def edit_button(message):
    msg = bot.send_message(message.chat.id, "Введите дату, номер задачи и новый текст (пример: Сегодня 1 Новый текст):", reply_markup=main_keyboard())
    bot.register_next_step_handler(msg, edit_step)

def edit_step(message):
    user_id = str(message.from_user.id)
    try:
        date, num, new_text = message.text.split(maxsplit=2)
        parsed_date = parse_date(date)
        if not parsed_date:
            bot.send_message(message.chat.id, "Неверный формат даты.", reply_markup=main_keyboard())
            return
        num = int(num) - 1
        if user_id in todos and parsed_date in todos[user_id] and 0 <= num < len(todos[user_id][parsed_date]):
            if len(new_text.strip()) < 3:
                bot.send_message(message.chat.id, "Ошибка: задача должна содержать не менее 3 символов.", reply_markup=main_keyboard())
                return
            todos[user_id][parsed_date][num] = new_text
            save_todos()
            bot.send_message(message.chat.id, f"Задача №{num+1} на дату {escape_markdown(date)} изменена.", parse_mode='MarkdownV2', reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "Задача с таким номером не найдена.", reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: дата номер_задачи новый_текст", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Удалить')
def delete_button(message):
    msg = bot.send_message(message.chat.id, "Введите дату и номер задачи для удаления (пример: Сегодня 1):", reply_markup=main_keyboard())
    bot.register_next_step_handler(msg, delete_step)

def delete_step(message):
    user_id = str(message.from_user.id)
    try:
        date, num = message.text.split(maxsplit=1)
        parsed_date = parse_date(date)
        if not parsed_date:
            bot.send_message(message.chat.id, "Неверный формат даты. Используйте сегодня, завтра, послезавтра или дд.мм.гггг", reply_markup=main_keyboard())
            return
        num = int(num) - 1
        if user_id in todos and parsed_date in todos[user_id] and 0 <= num < len(todos[user_id][parsed_date]):
            removed = todos[user_id][parsed_date].pop(num)
            if not todos[user_id][parsed_date]:
                del todos[user_id][parsed_date]
            save_todos()
            bot.send_message(
                message.chat.id,
                f"Задача {escape_markdown(removed)} удалена с даты {escape_markdown(date)}.",
                reply_markup=main_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "Задача с таким номером не найдена.", reply_markup=main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: дата номер_задачи", reply_markup=main_keyboard())

@bot.message_handler(commands=['help', 'random', 'add', 'all', 'print', 'edit', 'delete'])
def fallback(message):
    bot.send_message(message.chat.id, "Пожалуйста, используйте кнопки для управления задачами.", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Старт')
def start_button(message):
    bot.send_message(message.chat.id, "Бот готов к работе! Выбирай действие ниже 👇", reply_markup=main_keyboard())

bot.polling(none_stop=True)


