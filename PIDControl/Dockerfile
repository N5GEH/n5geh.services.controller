FROM python:3.7-alpine

ADD PID4FIWARE.py /
ADD filip /

RUN pip install requests
RUN pip install pyyaml

WORKDIR /app

COPY . /app

CMD [ "python", "./PID4FIWARE.py" ]
