FROM python:3.8

RUN mkdir -p /home/binance-profit-loss
WORKDIR /home/binance-profit-loss

COPY requirements.txt /home/binance-profit-loss

RUN pip install -r /home/binance-profit-loss/requirements.txt

COPY . /home/binance-profit-loss