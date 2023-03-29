# syntax=docker/dockerfile:1
FROM python:3.9-slim
WORKDIR /app
RUN pip install -U filip==0.2.4
RUN pip install pysimpleguiweb && pip install --upgrade remi
COPY ./ControllerPanel.py /app/ControllerPanel.py

EXPOSE 80

CMD [ "python", "./ControllerPanel.py" ]