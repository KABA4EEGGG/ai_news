FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04
WORKDIR /ai_news

RUN apt update && \
    apt install --no-install-recommends -y build-essential software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt install --no-install-recommends -y python3.10 python3-pip python3-setuptools python3-distutils && \
    apt clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /ai_news/req.txt
RUN python3.10 -m pip install --upgrade pip && \
    python3.10 -m pip install --no-cache-dir -r /ai_news/req.txt
COPY . .

EXPOSE 80

