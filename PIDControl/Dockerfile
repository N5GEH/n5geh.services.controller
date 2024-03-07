# syntax=docker/dockerfile:1

# Call this Dockerfile in the upper directory: docker build -f PIDControl/Dockerfile --tag pid4fiware .
FROM python:3.9-slim
WORKDIR /app
COPY ./controller4fiware /app
COPY PIDControl/PID4FIWARE.py /app/PID4FIWARE.py
COPY PIDControl/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

CMD [ "python", "./PID4FIWARE.py" ]