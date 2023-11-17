FROM python:3.11-alpine
WORKDIR /APP
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python","scheduler.py"]