from typing import Union

from fastapi import FastAPI
from ai_news_classification import pipeline
import sys
import os


app = FastAPI()


@app.get("/predict")
def base_predict(file_path: str):
    """
    Роут для классификации и дедубликации
    """
    if os.path.exists(file_path): # проверка на наличие файла
        pipeline.launch_pipeline(file_path)
        return "Успех. Результат находится в папке ai_news/data/output_data"
    else:
        return "Проверьте првильность написаниия пути до файла"
