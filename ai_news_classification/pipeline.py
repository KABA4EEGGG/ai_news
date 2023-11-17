import os
import time
from typing import List, Dict

from tqdm import tqdm
import numpy as np
import pandas as pd

from models.models import predict_zero_shot
from models.models import compute_similarity

import asyncio
import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler

host_db, user_db, db, password_db = os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_USER"), \
    os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_PASSWORD")
if not any(i for i in [host_db, user_db, db, password_db]):
    exit("Error: no env for db")


async def input_data() -> pd.DataFrame:
    """
    Запрос в db и преобразование данных в датафрейм, а также очистка таблицы data_parse

    Args:
        path (str): Путь до входного файла

    Returns:
        pd.DataFrame : Входная дата в виде датафрейма
    """
    conn = await asyncpg.connect(host=host_db, user=user_db, database=db, password=password_db)
    data = await conn.fetch('''SELECT * FROM data_parse ''')
    await conn.execute('''DELETE FROM data_parse ''')
    #await conn.close()
    columns_parse = ('name_channel', 'msg_id', 'msg_text', 'msg_time')
    return pd.DataFrame(data, columns=columns_parse)


def handle_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Обработка входного датафрейма:
    1. Удаление ненужных стоблцов
    2. удаление явных дубликатов
    3. Удаление ненужных метаданных

    Args:
        df (pd.DataFrame): Входной датафрейм

    Returns:
        pd.DataFrame: Датафрейм, готовый для классификации
    """
    # Удаление ненужных столбцов
    df = df[['msg_text']]

    # Удаление явных дубликатов
    df = df.drop_duplicates(keep=False, ignore_index=True)

    # Удаление ненужных метаданных
    df = df.replace(to_replace=r"(?<=\[).+?(?=\])", value="", regex=True)
    df = df.replace(to_replace=r"\([^)]*\)", value="", regex=True)
    df = df.replace(to_replace=r"(@)\w+", value="", regex=True)
    df = df.replace(
        to_replace=r"^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$",
        value="", regex=True)
    df = df.replace(to_replace=r"[]", value='')

    return df


def classify_data(df: pd.DataFrame, post_themes: List[str], default_theme: str) -> pd.DataFrame:
    """
    Классификация всех постов по заданным тематикам

    Args:
        df (pd.DataFrame): Датафрейм с постами
        post_themes (List[str]): Темы постов
        default_theme (str): Тема постов, которые не получилось классифицировать

    Returns:
        pd.DataFrame: Датафрейм с номым добавленным полем: 'Label'
    """
    df['Label'] = np.nan
    for indx, paper in enumerate(tqdm(df['msg_text'])):
        try:
            proba = predict_zero_shot(paper, post_themes)
            df['Label'].iloc[indx] = post_themes[np.argmax(proba)]
        except:
            df['Label'].iloc[indx] = default_theme

    return df


def fill_storage(df: pd.DataFrame, post_themes: List[str]) -> Dict[str, List[str]]:
    """
    Наполнение хранилища уникальными и насыщенными постами

    Args:
        df (pd.DataFrame): Размеченный датафрейм постов
        post_themes (List[str]): Тематики постов

    Returns:
        Dict[str, List[str]]: Ключ - тема поста, значения - тексты постов
    """

    # Создадим хранилище
    storage: Dict[str, List[str]] = {}

    for post_theme in post_themes:

        theme_posts = df['msg_text'].loc[df['Label'] == post_theme].to_list()
        # Рассчитаем кол-во постов по каждой из тематик
        # Если кол-во меньше 5, то берем все посты
        # Иначе по 5
        total_theme_posts = len(theme_posts)
        min_posts_amount = total_theme_posts if total_theme_posts < 5 else 5
        storage[post_theme] = theme_posts[:min_posts_amount]
        posts = theme_posts[min_posts_amount:]

        for post in posts:
            input_posts = [post for post in storage[post_theme]] + [post]
            scores = compute_similarity(input_posts)
            max_similarity_indx = np.argmax(scores)
            if scores[max_similarity_indx] > 90:
                if len(post) > len(storage[post_theme][max_similarity_indx]):
                    storage[post_theme][max_similarity_indx] = post

    return storage


async def output_data(classified_data: pd.DataFrame, storage: Dict[str, List[str]]) -> None:
    """
    Сохранение размеченного датасета в csv файл
    Сохранение 10 самых уникальных и насыщенных постов по всем тематикам в txt файл

    Args:
        classified_data (pd.DataFrame): Размеченный датафрейм
        storage (Dict[str, List[str]]): Хранилище постов. Ключ - тема поста, значение - тексты постов

    Rerurns:
        None
    """
    conn = await asyncpg.connect(host=host_db, user=user_db, database=db, password=password_db)
    await conn.execute('''CREATE TABLE IF NOT EXISTS output_data 
                        (theme VARCHAR(35), text text''')
    # Сохранение уникальных постов
    for key in storage.keys():
        for text in storage[key]:
            await conn.execute('''INSERT INTO output_data VALUES ($1, $2)''', key, text)
    await conn.close()


async def launch_pipeline():
    """
    Запуск пайплайна

    Args:
        file_path (str): Путь до входного файла

    Returns:
        None
    """

    post_themes = ['Финансы', 'Технологии', 'Политика',
                   'Шоубизнес', 'Fashion', 'Криптовалюта', 'Путешествия',
                   'Образование', 'Развлечения', 'Общее']
    default_theme = 'Общее'

    data = await input_data()
    data = handle_data(data)
    classified_data = classify_data(data, post_themes, default_theme)
    storage = fill_storage(classified_data, post_themes)
    await output_data(classified_data, storage)


async def main():
    time.sleep(30)
    await launch_pipeline()
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(launch_pipeline, 'interval', minutes=30)
    time.sleep(300)
    scheduler.start()


def _compare_with_other_posts(storage: Dict[str, List[str]], post: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Сверяем введенный пост на степень сходства с 10 постами в хранилище
    Если степень сходства > 0.9 с записью из хранилища,
    то выбирается более длинная запись, так как она более насыщена.
    Если степень сходства > 0.9 с несколькими записями их хранилища,
    то выбирается с максимальной степенью сходства

    Args:
        storage (Dict[str,List[str]]): Хранилище постов. Ключ - тема поста, значение - тексты постов
        post (Dict[str, str]):

    Returns:
        Dict[str, List[str]]: Измененное/неизмененное хранилище
    """


def _compute_min_post_amount_output(df: pd.DataFrame) -> int:
    """
    Расчет количества уникальных и насыщенных постов для вывода:
    За минимальное количество будем брать 10.
    Но если по какой-либо из тематик кол-во постов меньше 10,
    то берем минимальное количество среди всех тематик и выводим

    Args:
        df (pd.DataFrame): Размеченный датафрейм

    Return:
        int: Количество постов для вывода
    """
    raise NotImplementedError


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()

# TODO: написать _compare_with_other_posts, _compute_min_post_amount_output, написать try-except, где необходимо
