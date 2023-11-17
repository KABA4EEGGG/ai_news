import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import F
#Вытаскиваем токен бота из env
bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    exit("Error: no token provided")

host_db, user_db, db, password_db = os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_USER"),\
                                 os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_PASSWORD")
if not any(i for i in [host_db, user_db, db, password_db]):
    exit("Error: no env for db")

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=bot_token)
# Диспетчер
dp = Dispatcher(storage=MemoryStorage())
# Клавиатуры
buttons = [[types.KeyboardButton(text="Let's go!")],
            [types.KeyboardButton(text="Stop")]]
keyboard = types.ReplyKeyboardMarkup(keyboard=buttons,resize_keyboard=True)

keyboard_insert = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Stop")]],\
                                            resize_keyboard=True)
# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global user_name
    user_name = str(message.from_user.first_name)
    await message.answer(text=f"Привет, *{user_name}*\! Это бот AInews, согласен получать новости?",\
                          reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
# Хэндлер на Let's go!
@dp.message(F.text=="Let's go!")
async def insert_user(message: types.Message):
    await con.execute('''INSERT INTO users
                       VALUES ($1, $2) on conflict (chat_id) do nothing''',\
                          message.chat.id, message.from_user.username)
    await message.answer("Супер, теперь жди новости!", reply_markup=keyboard_insert)
# Хэндлер на Stop
@dp.message(F.text=="Stop")
async def delete_users(message: types.Message):
    await con.execute('''DELETE FROM users
                        WHERE chat_id = ($1)''', message.chat.id)
    await message.answer("До новых встреч!", reply_markup=keyboard)

#Функция для подготовки вывода новостей
def news_message(theme:str, text:str) -> str:
    res = ""
    return res
#Отправка новостей пользователям
async def send_news():
    rows = await con.fetch('''SELECT * FROM users''')
    result = await con.fetch('''SELECT theme, MIN(text) FROM output_data GROUP BY theme''')
    for row in rows:
        for theme in result['theme']:
            await bot.send_message(text=f"{theme}:{result['text']}",chat_id=row['chat_id'])

# Запуск процесса пуллинга новых апдейтов и создание соединения с бд + создание таблицы
async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_news, "interval", seconds=5000)
    global con
    con = await asyncpg.connect(host=host_db, user=user_db, database=db, password=password_db)
    await con.execute('''CREATE TABLE IF NOT EXISTS users 
                        (chat_id int UNIQUE, user_name VARCHAR(100))''')
    try:
        scheduler.start()
        await dp.start_polling(bot)
                
    finally:
        scheduler.shutdown(wait=False)
        await dp.storage.close()
        await bot.session.close()
        await con.close()


if __name__ == "__main__":
    asyncio.run(main())