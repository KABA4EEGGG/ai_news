from typing import Union

from fastapi import FastAPI, Body
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from ai_news_classification import pipeline
import sys
import os

import pandas as pd
app = FastAPI()
templates = Jinja2Templates(directory="./app/templates")
@app.get("/")
def root():
    return FileResponse("./app/html/index.html")

@app.post("/predict")
def base_predict(data=Body()):
    """
    Роут для классификации и дедубликации
    """
    if os.path.exists(data["pathdata"]): # проверка на наличие файла
        pipeline.launch_pipeline(data["pathdata"])
        return "Успех. Результат находится в папке ai_news/data/output_data"
    else:
        return "Проверьте првильность написаниия пути до файла"


@app.get("/news/{category}")
async def news_view(category: str):
    return