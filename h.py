import telebot
from random import choice
import re

token = ''

bot = telebot.TeleBot(token)

RANDOM_TASKS = ['Написать Гвидо письмо', 'Выучить Python', 'Записаться на курс в Нетологию', 'Посмотреть 4 сезон Рик и Морти']

todos = dict()


HELP = '''
Список доступных команд:
* print  - напечатать все задачи на заданную дату
* add - добавить задачу
* random - добавить на сегодня случайную задачу
* help - Напечатать help
* all - Вывод всех задач
* edit - изменение текста задачи
* delete - удаление задачи по порядковому номеру в списке
'''

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def add_todo(date, task):
    date = date.lower()
    if todos.get(date) is not None:
        todos[date].append(task)
    else:
        todos[date] = [task]


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, HELP)


@bot.message_handler(commands=['random'])
def random(message):
    task = choice(RANDOM_TASKS)
    add_todo('сегодня', task)
    bot.send_message(message.chat.id, f'Задача {task} добавлена на сегодня')


@bot.message_handler(commands=['add'])
def add(message):
    try:
        _, date, task = message.text.split(maxsplit=2)
        if len(task.strip()) < 3:
            bot.send_message(message.chat.id, "Ошибка: задача должна содержать не менее 3 символов.")
            return
        add_todo(date, task)
        bot.send_message(message.chat.id, f'Задача {task} добавлена на дату {date}')
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: /add дата задача")

@bot.message_handler(commands=['all'])
def all_tasks(message):
    if not todos:
        bot.send_message(message.chat.id, "Нет задач")
        return
    result = ""
    for date, tasks in todos.items():
        result += f"*{escape_markdown(date).title()}*\n"
        for i, task in enumerate(tasks, 1):
            result += f"{i}\\. {escape_markdown(task)}\n"
        result += "\n"
    bot.send_message(message.chat.id, result.strip(), parse_mode='MarkdownV2')

@bot.message_handler(commands=['print'])
def print_(message):
    try:
        date = message.text.split()[1].lower()
        if date in todos:
            tasks = ''
            for task in todos[date]:
                tasks += f'[ ] {task}\n'
        else:
            tasks = 'Такой даты нет'
        bot.send_message(message.chat.id, tasks)
    except IndexError:
        bot.send_message(message.chat.id, "Пожалуйста, укажите дату после команды /print")

@bot.message_handler(commands=['edit'])
def edit_task(message):
    try:
        _, date, num, new_text = message.text.split(maxsplit=3)
        date = date.lower()
        num = int(num) - 1
        if date in todos and 0 <= num < len(todos[date]):
            if len(new_text.strip()) < 3:
                bot.send_message(message.chat.id, "Ошибка: задача должна содержать не менее 3 символов.")
                return
            todos[date][num] = new_text
            bot.send_message(message.chat.id, f"Задача №{num+1} на дату {date} изменена.")
        else:
            bot.send_message(message.chat.id, "Задача с таким номером не найдена.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: /edit дата номер_задачи новое_описание")

@bot.message_handler(commands=['delete'])
def delete_task(message):
    try:
        _, date, num = message.text.split(maxsplit=2)
        date = date.lower()
        num = int(num) - 1
        if date in todos and 0 <= num < len(todos[date]):
            removed = todos[date].pop(num)
            bot.send_message(message.chat.id, f"Задача '{removed}' удалена с даты {date}.")
            if not todos[date]:
                del todos[date]
        else:
            bot.send_message(message.chat.id, "Задача с таким номером не найдена.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, используйте формат: /delete дата номер_задачи")



bot.polling(none_stop=True)