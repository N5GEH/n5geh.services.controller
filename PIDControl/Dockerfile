# syntax=docker/dockerfile:1

# Call this Dockerfile in the upper directory: docker build -f PIDControl/Dockerfile --tag pid4fiware .
FROM python:3.9-slim
WORKDIR /app
RUN pip install -U filip==0.2.4
RUN pip install simple-pid
COPY ./Controller.py /app/Controller.py
COPY ./keycloak_token_handler /app/keycloak_token_handler
COPY PIDControl/PID4FIWARE.py /app/PID4FIWARE.py
COPY PIDControl/config /app/config

CMD [ "python", "./PID4FIWARE.py" ]