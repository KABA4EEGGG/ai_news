import os
import sys
from typing import List, Dict, Tuple

from tqdm import tqdm
import numpy as np
import pandas as pd


from models.models import predict_zero_shot
from models.models import compute_similarity

def input_data(path: str) -> pd.DataFrame:
    """
    Преобразование входного файла в датафрейм

    Args:
        path (str): Путь до входного файла

    Returns:
        pd.DataFrame : Входная дата в виде датафрейма
    """
    return pd.read_csv(path)


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
    df = df[['text']]

    # Удаление явных дубликатов
    df = df.drop_duplicates(keep=False, ignore_index=True)

    # Удаление ненужных метаданных
    df = df.replace(to_replace=r"(?<=\[).+?(?=\])", value="", regex=True)
    df = df.replace(to_replace=r"\([^)]*\)", value="", regex=True)
    df = df.replace(to_replace=r"(@)\w+", value="", regex=True)
    df = df.replace(
        to_replace=r"^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$", value="", regex=True)
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
    for indx, paper in enumerate(tqdm(df['text'])):
        try:
            proba = predict_zero_shot(paper, post_themes)
            df['Label'].iloc[indx] = post_themes[np.argmax(proba)]
        except:
            df['Label'].iloc[indx] = default_theme

    return df


def fill_storage(df: pd.DataFrame, post_themes: List[str]) -> Tuple[Dict[str, List[str]], int]:
    """
    Наполнение хранилища уникальными и насыщенными постами

    Args:
        df (pd.DataFrame): Размеченный датафрейм постов
        post_themes (List[str]): Тематики постов

    Returns:
        Dict[str, List[str]]: Ключ - тема поста, значения - тексты постов
        int: Количество постов, которое мы заменили
    """

    # Создадим хранилище
    storage: Dict[str, List[str]] = {}

    for post_theme in post_themes:

        theme_posts = df['text'].loc[df['Label'] == post_theme].to_list()
        # Рассчитаем кол-во постов по каждой из тематик
        # Если кол-во меньше 10, то берем все посты
        # Иначе по 10
        total_theme_posts = len(theme_posts)
        min_posts_amount = total_theme_posts if total_theme_posts < 10 else 10
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


def output_data(classified_data: pd.DataFrame, storage: Dict[str, List[str]]) -> None:
    """
    Сохранение размеченного датасета в csv файл
    Сохранение 10 самых уникальных и насыщенных постов по всем тематикам в txt файл

    Args:
        classified_data (pd.DataFrame): Размеченный датафрейм
        storage (Dict[str, List[str]]): Хранилище постов. Ключ - тема поста, значение - тексты постов

    Rerurns:
        None
    """
    # Сохранение датафрейма
    df_output_path = os.path.join(
        '..', 'data', 'output_data', 'labeled_data.csv')
    classified_data.to_csv(df_output_path, index=False)

    # Сохранение уникальных постов
    posts_output_path = os.path.join(
        '..', 'data', 'output_data', 'unique_posts.txt')
    with open(posts_output_path, 'w', encoding='utf-8') as f:
        for post_theme, posts in storage.items():
            f.write(post_theme.upper() + '\n')
            for indx, post in enumerate(posts, start=1):
                f.write(f'{indx}) {post}' + '\n')
            f.write('-'*100 + '\n')


def launch_pipeline(file_path: str = r'D:\projects\ai_news\data\test.csv'):
    """
    Запуск пайплайна

    Args:
        file_path (str): Путь до входного файла

    Returns:
        None
    """

    data_path = file_path
    # post_themes = ['Блоги', 'Новости и СМИ', 'Развлечения и юмор', 'Технологии',
    #                'Экономика', 'Бизнес и стартапы', 'Криптовалюты', 'Путешествия',
    #                'Маркетинг, PR, реклама', 'Психология', 'Дизайн', 'Политика',
    #                'Искусство', 'Право', 'Образование и познавательное', 'Спорт',
    #                'Мода и красота', 'Здоровье и медицина', 'Картинки и фото',
    #                'Софт и приложения', 'Видео и фильмы', 'Музыка', 'Игры', 'Цитаты'
    #                'Еда и кулинария', 'Рукоделие', 'Финансы', 'Шоубиз', 'Другое']
    post_themes = ['Финансы', 'Технологии', 'Политика',
                   'Шоубиз', 'Fashion', 'Крипта', 'Путешествия/релокация',
                   'Образовательный контент', 'Развлечения', 'Общее']
    default_theme = 'Общее'

    data = input_data(data_path)
    data = handle_data(data)
    classified_data = classify_data(data, post_themes, default_theme)
    storage = fill_storage(classified_data, post_themes)
    output_data(classified_data, storage)


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


# TODO: написать _compare_with_other_posts, _compute_min_post_amount_output, написать try-except, где необходимо


