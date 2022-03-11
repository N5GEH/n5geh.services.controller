# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

PID controller with Fiware interface
"""

import time
import os
from simple_pid import PID
import requests

from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.context import NamedCommand, ContextEntity, NamedContextAttribute

import signal
import sys


# TODO
#  1. how to let controller state pending (if the connection to sensor/actuator fails)
#     shut down the controller and keep the container alive? or just let the container die?
#  2. how to tune the control parameters during run time? The parameters can be change by sending requests to CB.
#     Maybe another container?
#  3. write a small tutorial
class Control:
    """PID controller with FIWARE interface"""

    def __init__(self):
        """Initialization"""

        # use envirnment variables  
        os.environ["CONFIG_FILE"] = "False"

        # define parameters
        self.params = {}
        self.params['name'] = os.getenv("NAME", 'PID_1')
        # TODO hard coded?
        self.params['type'] = "PID_Controller"
        self.params['setpoint'] = float(os.getenv("SETPOINT", '293.15'))
        # TODO how to tune the parameters?
        # TODO reverse mode can be activate by passing negative tunings to controller
        self.params['Kp'] = float(os.getenv("KP", '1.0'))
        self.params['Ki'] = float(os.getenv("KI", '100'))
        self.params['Kd'] = float(os.getenv("KD", '0'))
        self.params['lim_low'] = float(os.getenv("LIM_LOW", '0'))
        self.params['lim_high'] = float(os.getenv("LIM_HIGH", '100'))
        self.params['pause_time'] = float(os.getenv("PAUSE_TIME", 0.2))
        self.params['sensor_entity_name'] = os.getenv("SENSOR_ENTITY_NAME", '')
        # TODO multiple attributes allowed? If not, why not use the term attr
        self.params['sensor_attrs'] = os.getenv("SENSOR_ATTRS", '')
        self.params['actuator_entity_name'] = os.getenv("ACTUATOR_ENTITY_NAME", '')
        self.params['actuator_type'] = os.getenv("ACTUATOR_TYPE", '')
        self.params['actuator_command'] = os.getenv("ACTUATOR_COMMAND", '')
        self.params['actuator_command_value'] = self.params['actuator_command'] + '_info'
        self.params['config_Filip'] = ''  # dummy value
        # TODO new params, check if we need it all
        self.params['service'] = os.getenv("FIWARE_SERVICE", '')
        self.params['service_path'] = os.getenv("FIWARE_SERVICE_PATH", '')
        self.params['cb_url'] = os.getenv("CB_URL", "http://localhost:1026")
        # self.params['iota_url'] = os.getenv("IOTA_URL", "http://localhost:4041")

        # simple pid instance
        # TODO use the reverse for the tuning parameters, or change the env parameters to Ki and Kd
        self.pid = PID(self.params['Kp'], self.params['Ki'], self.params['Kd'],
                       setpoint=self.params['setpoint'],
                       output_limits=(self.params['lim_low'], self.params['lim_high'])
                       )

        # Additional parameters
        # TODO how to use this para
        self.auto_mode = True
        self.y = None
        self.x_act = self.params['setpoint']  # set the initial control value to set point

        # Create the fiware header
        fiware_header = FiwareHeader(service=self.params['service'], service_path=self.params['service_path'])

        # Create orion context broker client
        self.ORION_CB = ContextBrokerClient(url=self.params['cb_url'], fiware_header=fiware_header)
        # self.IOTA = IoTAClient(url=self.params['cb_url'], fiware_header=fiware_header)

    def create_entity(self):
        """Creates entitiy of PID controller in orion context broker"""
        # TODO we communicate via 1026, how to change the parameters of the controller
        try:
            self.ORION_CB.get_entity(entity_id=self.params['name'],
                                     entity_type=self.params['type'])
            print('Entity name already assigned')
            # TODO how to update the entity? or delete the controller
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise  # throw other errors except "entity not found"
            print('[INFO]: Create new PID entity')
            # TODO better entity name?
            #  To avoid duplicated names
            #  For example: heater(actuator_device)_pid(algorithms)_controller_1(random_number?)
            # TODO entity type is now hard coded to PID_Controller
            pid_entity = ContextEntity(id=f'{self.params["name"]}',
                                       type=self.params['type'])
            cb_attrs = []
            for attr in ['Kp', 'Ki', 'Kd', 'lim_low', 'lim_high', 'setpoint']:
                cb_attrs.append(NamedContextAttribute(name=attr,
                                                      type="Number",
                                                      value=self.params[attr]))
            pid_entity.add_attributes(attrs=cb_attrs)
            self.ORION_CB.post_entity(entity=pid_entity, update=True)

    def update_params(self):
        """Read PID parameters of entity in context broker and updates PID control parameters"""
        # TODO if the request fails, shut down the controller and keep the container alive?
        #  or just let the container die?
        # read controller parameters from context broker
        # that means it is possible to change the parameters via CB
        for attr in ['Kp', 'Ki', 'Kd', 'lim_low', 'lim_high', 'setpoint']:
            self.params[attr] = float(
                self.ORION_CB.get_attribute_value(entity_id=self.params['name'],
                                                  entity_type=self.params['type'],
                                                  attr_name=attr))
        try:
            # read the current actuator values
            self.y = self.ORION_CB.get_attribute_value(entity_id=self.params['actuator_entity_name'],
                                                       entity_type=self.params['actuator_type'],
                                                       attr_name=self.params['actuator_command_value'])
            if not isinstance(self.y, (int, float)):
                self.y = None

            # read the control value from sensor
            x = self.ORION_CB.get_attribute_value(entity_id=self.params['sensor_entity_name'],
                                                  attr_name=self.params['sensor_attrs'])
            # set 0 if empty
            # TODO check the x value here
            print(f"attribute value of the sensor: x=({x})")
            if x == '" "':
                x = '0'
            # convert to float
            self.x_act = float(x)
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.auto_mode = False
            print("Connection fails")
        else:
            # If no errors are raised
            self.auto_mode = True
        # TODO how to allow warm star? use self.pid.set_auto_mode(True, last_output=self.y)
        if not self.auto_mode:
            self.pid.set_auto_mode(True, last_output=self.y)

        # update PID parameters
        self.pid.tunings = (self.params['Kp'], self.params['Ki'], self.params['Kd'])
        self.pid.output_limits = (self.params['lim_low'], self.params['lim_high'])
        self.pid.setpoint = self.params['setpoint']

    def run(self):
        """Calculation of PID output"""

        # read sensor value (actual value)
        # TODO is it possible to use subscription for the data transfer?
        #  Options if work with subscription:
        #   1. controller deal with the notification from CB
        #   2. the notification is sent directly to the CB (e.g. x_act of the controller entity)
        # subscription = {
        #     "description": "Auto update of the control parameter",
        #     "subject": {
        #         "entities": [
        #             {
        #                 "id": self.params['sensor_entity_name'],
        #             }
        #         ],
        #     },
        #     "notification": {
        #         'http': {'url': self.params['cb_url']},
        #         'attrs': ['temperature'],
        #     },
        #     "throttling": 0
        # }
        try:
            # TODO if we need 2 flag to indicate the connectivity of sensor and actuator?
            if self.auto_mode:
                # calculate PID output
                print(f"x_act ={self.x_act}, x_set = {self.params['setpoint']}")
                self.y = self.pid(self.x_act)
                # build command
                command = NamedCommand(name=self.params['actuator_command'], value=round(self.y, 3))
                self.ORION_CB.post_command(entity_id=self.params['actuator_entity_name'],
                                           entity_type=self.params['actuator_type'],
                                           command=command)
                print(f"output: {self.y}")
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.auto_mode = False
            print("Connection fails")
            # TODO reset()?


def exit_handler(*args):
    # TODO not used yet
    pid_controller.ORION_CB.delete_entity(entity_id=pid_controller.params['name'],
                                          entity_type=pid_controller.params['type'])
    print("Entity deleted")
    sys.exit(0)


if __name__ == "__main__":
    pid_controller = Control()
    pid_controller.create_entity()
    # # TODO maybe delete the entity if the program is shut down
    # # Delete the controller entity before the container stops
    # signal.signal(signal.SIGTERM, exit_handler)
    while True:
        pid_controller.update_params()
        pid_controller.run()
        time.sleep(pid_controller.params['pause_time'])

    # Delete controller entity before program is terminated
    # try: ...
    # finally:
    #     # Delete the controller entity if the container stops
    #     exit_handler()
    #     raise

