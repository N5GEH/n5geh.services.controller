"""

This script is mainly based on the Exercise 5 of FiLiP. If you want to totally understand this script,
please go through the exercises of FiLiP: https://github.com/N5GEH/FiLiP/tree/master/tutorials/ngsi_v2

"""
import json
from pathlib import Path
import time
from typing import List
from urllib.parse import urlparse
import paho.mqtt.client as mqtt


from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient, QuantumLeapClient
from filip.clients.mqtt import IoTAMQTTClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.iot import \
    Device, \
    PayloadProtocol, \
    ServiceGroup
from filip.utils.cleanup import clear_context_broker, clear_iot_agent

from simulation_model import SimulationModel


# ## Parameters
# ToDo: Enter your context broker host and port, e.g http://localhost:1026
CB_URL = "http://localhost:1026"
# ToDo: Enter your IoT-Agent host and port, e.g http://localhost:4041
IOTA_URL = "http://localhost:4041"
# ToDo: Enter your Quantum Leap host and port, e.g http://localhost:8668
QL_URL = "http://localhost:8668"
# ToDo: Enter your mqtt broker url from your local network, e.g mqtt://localhost:1883
MQTT_BROKER_URL_EXPOSED = "mqtt://localhost:1883"
# ToDo: Enter your mqtt broker url from the docker network, e.g mqtt://mosquitto:1883
MQTT_BROKER_URL_INTERNAL = "mqtt://mosquitto:1883"
# ToDo: If required enter your username and password
MQTT_USER = ""
MQTT_PW = ""

# FIWARE-Service
SERVICE = 'controller'
# FIWARE-Servicepath
SERVICE_PATH = '/'

APIKEY = "buildings"

# Path to read json-files from previous exercises
READ_GROUPS_FILEPATH = \
    Path("fiware_groups.json")
READ_DEVICES_FILEPATH = \
    Path("devices.json")


def simulation(
        TEMPERATURE_MAX=10,  # maximal ambient temperature
        TEMPERATURE_MIN=-5,  # minimal ambient temperature
        TEMPERATURE_ZONE_START=10,  # start value of the zone temperature
        T_SIM_START=0,  # simulation start time in seconds
        T_SIM_END=24 * 60 * 60,  # simulation end time in seconds
        COM_STEP=60 * 15,  # 1 min communication step in seconds
        SLEEP_TIME=0.2  # sleep time between every simulation step
):
    # create a fiware header object
    fiware_header = FiwareHeader(service=SERVICE,
                                 service_path=SERVICE_PATH)

    # instantiate simulation model
    sim_model = SimulationModel(t_start=T_SIM_START,
                                t_end=T_SIM_END,
                                temp_max=TEMPERATURE_MAX,
                                temp_min=TEMPERATURE_MIN,
                                temp_start=TEMPERATURE_ZONE_START)

    # Create clients and restore devices and groups from files
    with open(READ_GROUPS_FILEPATH, "r") as f:
        groups_dict = json.load(f)
        groups = [ServiceGroup.model_validate(group_dict)
                  for group_dict in groups_dict]
    with open(READ_DEVICES_FILEPATH, "r") as f:
        devices_dict = json.load(f)
        devices = [Device.model_validate(device_dict)
                   for device_dict in devices_dict]
    cbc = ContextBrokerClient(url=CB_URL, fiware_header=fiware_header)
    iotac = IoTAClient(url=IOTA_URL, fiware_header=fiware_header)
    iotac.post_groups(service_groups=groups, update=True)
    iotac.post_devices(devices=devices, update=True)

    # Get the device configurations from the server
    weather_station = iotac.get_device(device_id="device:001")
    zone_temperature_sensor = iotac.get_device(device_id="device:002")
    heater = iotac.get_device(device_id="device:003")

    # Get the service group configurations from the server
    group = iotac.get_group(resource="/iot/json", apikey=APIKEY)

    #  Create a http subscriptions that get triggered by updates of your
    #  device attributes and send data to Quantum Leap.
    qlc = QuantumLeapClient(url=QL_URL, fiware_header=fiware_header)

    qlc.post_subscription(entity_id=weather_station.entity_name,
                          entity_type=weather_station.entity_type,
                          cb_url="http://orion:1026",
                          ql_url="http://quantumleap:8668",
                          throttling=0)

    qlc.post_subscription(entity_id=zone_temperature_sensor.entity_name,
                          entity_type=zone_temperature_sensor.entity_type,
                          cb_url="http://orion:1026",
                          ql_url="http://quantumleap:8668",
                          throttling=0)

    qlc.post_subscription(entity_id=heater.entity_name,
                          entity_type=heater.entity_type,
                          cb_url="http://orion:1026",
                          ql_url="http://quantumleap:8668",
                          throttling=0)

    # create a MQTTv5 client with paho-mqtt and the known groups and devices.
    mqttc = IoTAMQTTClient(protocol=mqtt.MQTTv5,
                           devices=[weather_station,
                                    zone_temperature_sensor,
                                    heater],
                           service_groups=[group])
    # set user data if required
    mqttc.username_pw_set(username=MQTT_USER, password=MQTT_PW)

    #  Implement a callback function that gets triggered when the
    #  command is sent to the device. The incoming command should update the
    #  heater power of the simulation model
    def on_command(client, obj, msg):
        """
        Callback for incoming commands
        """
        # Decode the message payload using the libraries builtin encoders
        apikey, device_id, payload = \
            client.get_encoder(PayloadProtocol.IOTA_JSON).decode_message(
                msg=msg)
        # Update the heating power of the simulation model
        sim_model.heater_power = payload["heaterPower"]

        # Acknowledge the command.
        client.publish(device_id=device_id,
                       command_name=next(iter(payload)),
                       payload=payload)

    # Add the command callback to your MQTTClient. This will get
    #  triggered for the specified device_id
    mqttc.add_command_callback(device_id=heater.device_id,
                               callback=on_command)

    # connect to the mqtt broker and subscribe to your topic
    mqtt_url = urlparse(MQTT_BROKER_URL_EXPOSED)
    mqttc.connect(host=mqtt_url.hostname,
                  port=mqtt_url.port,
                  keepalive=60,
                  bind_address="",
                  bind_port=0,
                  clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                  properties=None)
    # subscribe to all incoming command topics for the registered devices
    mqttc.subscribe()

    # create a non-blocking thread for mqtt communication
    mqttc.loop_start()

    # define lists to store historical data
    history_weather_station = []
    history_zone_temperature_sensor = []
    history_heater_power = []

    # simulation without heater
    # Create a loop that publishes regularly a message to the broker
    #  that holds the simulation time "simtime" and the corresponding
    #  temperature "temperature" the loop should. You may use the `object_id`
    #  or the attribute name as key in your payload.
    print("Simulation starts")
    for t_sim in range(sim_model.t_start,
                       sim_model.t_end + int(COM_STEP),
                       int(COM_STEP)):
        # publish the simulated ambient temperature
        mqttc.publish(device_id=weather_station.device_id,
                      payload={"temperature": sim_model.t_amb,
                               "simtime": sim_model.t_sim})

        # publish the simulated zone temperature
        mqttc.publish(device_id=zone_temperature_sensor.device_id,
                      payload={"temperature": sim_model.t_zone,
                               "simtime": sim_model.t_sim})

        # publish the 'simtime' for the heater device
        mqttc.publish(device_id=heater.device_id,
                      payload={"simtime": sim_model.t_sim})

        # simulation step for next loop
        sim_model.do_step(int(t_sim + COM_STEP))
        # wait for one second before publishing the next values
        time.sleep(SLEEP_TIME)

        # Get corresponding entities and write values to history
        weather_station_entity = cbc.get_entity(
            entity_id=weather_station.entity_name,
            entity_type=weather_station.entity_type
        )
        # append the data to the local history
        history_weather_station.append(
            {"simtime": weather_station_entity.simtime.value,
             "temperature": weather_station_entity.temperature.value})

        # Get ZoneTemperatureSensor and write values to history
        zone_temperature_sensor_entity = cbc.get_entity(
            entity_id=zone_temperature_sensor.entity_name,
            entity_type=zone_temperature_sensor.entity_type
        )
        history_zone_temperature_sensor.append(
            {"simtime": zone_temperature_sensor_entity.simtime.value,
             "temperature": zone_temperature_sensor_entity.temperature.value})

        # Get ZoneTemperatureSensor and write values to history
        heater_entity = cbc.get_entity(
            entity_id=heater.entity_name,
            entity_type=heater.entity_type)
        history_heater_power.append(
            {"simtime": heater_entity.simtime.value,
             "heaterPower": sim_model.heater_power})

    # close the mqtt listening thread
    mqttc.loop_stop()
    # disconnect the mqtt device
    mqttc.disconnect()

    clear_iot_agent(url=IOTA_URL, fiware_header=fiware_header)
    clear_context_broker(url=CB_URL, fiware_header=fiware_header)

    return history_weather_station, history_zone_temperature_sensor, history_heater_power