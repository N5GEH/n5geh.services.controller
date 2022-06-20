# syntax=docker/dockerfile:1

# Call this Dockerfile in the upper directory: docker build -f PIDControl/Dockerfile --tag pid4fiware .

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
RUN pip install simple-pid
COPY ./Controller.py /app/Controller.py
COPY ./keycloak_token_handler /app/keycloak_token_handler
COPY PIDControl/PID4FIWARE.py /app/PID4FIWARE.py
COPY PIDControl/config /app/config

CMD [ "python", "./PID4FIWARE.py" ]