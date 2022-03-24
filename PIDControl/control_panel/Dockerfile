# syntax=docker/dockerfile:1

# stage 0
FROM alpine/git
WORKDIR /app
RUN git clone https://github.com/N5GEH/FiLiP.git

# stage 1
FROM python:3.9-slim
WORKDIR /app
COPY --from=0 /app/FiLiP /app/FiLiP
#COPY requirements.txt requirements.txt
#RUN pip install -r requirements.txt
RUN pip install -e /app/FiLiP
RUN pip install pysimpleguiweb && pip install --upgrade remi
COPY ./ControllerPanel.py /app/ControllerPanel.py

EXPOSE 80

CMD [ "python", "./ControllerPanel.py" ]