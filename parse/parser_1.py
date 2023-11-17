from telethon import TelegramClient
from typing import List
import asyncio
import datetime
import os
import logging
import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
logging.basicConfig(level=logging.INFO)
# get env
host_db, user_db, db, password_db = os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_USER"), \
    os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_PASSWORD")
if not any(i for i in [host_db, user_db, db, password_db]):
    exit("Error: no env for db")

phone_tg, pass_tg, api_id, api_hash = os.getenv("PHONE_NUMBER"), os.getenv("TELEGRAM_PASS"), \
    os.getenv("API_ID"), os.getenv("API_HASH")
if not any(i for i in [phone_tg, pass_tg, api_id, api_hash]):
    exit("Error: no env for tg")


async def parse(client: TelegramClient, channel_names: List[List[str]], time: int) -> List[str]:
    date_of_post = datetime.datetime.now() - datetime.timedelta(hours=time+3)
    print(date_of_post)
    results = []
    for channel_name in channel_names:
        channel = await client.get_entity(channel_name)
        messages = [msg async for msg in client.iter_messages(channel, reverse=True, offset_date=date_of_post)]
        result = [[str(message.sender_id), message.id, message.text, message.date] for message in messages
                  if message.text != ""]
        results += result
    return results


async def add_to_db(conn: asyncpg.connection.Connection, data: List[List[str]]):
    await conn.executemany('''INSERT INTO data_parse VALUES ($1, $2, $3, $4)''', data)

async def task(client, channel_names, time, con):
    results = await parse(client=client, channel_names=channel_names, time=time)
    await add_to_db(conn=con, data=results)

async def main(time: int = 6, channel_names: List[str] = []):
    #con = await asyncpg.connect(host=host_db, user=user_db, database=db, password=password_db)
    con = await asyncpg.connect(host=host_db, user=user_db, database=db, password=password_db)
    await con.execute('''CREATE TABLE IF NOT EXISTS data_parse 
                        (name_channel VARCHAR(35), msg_id int, msg_text text, msg_time time)''')
    client = TelegramClient('pgnews', api_id, api_hash)
    await client.start(phone=phone_tg, password=pass_tg)
    if not client.is_connected():
        await client.connect()
    await task(client,channel_names,time,con)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(task, 'interval', hours=6, args=(client,channel_names,time,con))
    scheduler.start()

    #con.close()
    #await client.log_out()
if __name__ == '__main__':
    channels_for_parsing = ['topor', 'infomoscow24', 'readovkanews',
                            'breakingmash', 'bazabazon']
    loop = asyncio.new_event_loop()
    loop.create_task(main(channel_names=channels_for_parsing))
    loop.run_forever()
