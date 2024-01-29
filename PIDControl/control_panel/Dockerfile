# syntax=docker/dockerfile:1
FROM python:3.9-slim
WORKDIR /app
COPY ./ControllerPanel.py /app/ControllerPanel.py
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
RUN pip install --upgrade remi
EXPOSE 80

CMD [ "python", "./ControllerPanel.py" ]