# syntax=docker/dockerfile:1

# stage 0
FROM alpine/git
WORKDIR /app
RUN git clone https://github.com/N5GEH/FiLiP.git

# stage 1
#FROM python:3.8-alpine
# Error occurs during the installation of packages when using alpine
FROM python:3.9
WORKDIR /app
COPY --from=0 /app/FiLiP /app/FiLiP
#COPY requirements.txt requirements.txt
#RUN pip install -r requirements.txt
RUN pip install -e /app/FiLiP
COPY . /app

CMD [ "python", "./PID4FIWARE.py" ]