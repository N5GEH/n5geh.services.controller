# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

Updated on Tue Mar 15 15:47:00 2022

@author: jdu

PID controller with Fiware interface
"""
import time
import os
from simple_pid import PID
import requests
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.context import NamedCommand, ContextEntity, NamedContextAttribute
from keycloak_token_handler.keycloak_python import KeycloakPython


class Control:
    """PID controller with FIWARE interface"""

    def __init__(self):
        """Initialization"""
        # # use envirnment variables
        # os.environ["CONFIG_FILE"] = "False"
        # define parameters
        self.params = {}
        self.params['controller_name'] = os.getenv("CONTROLLER_NAME", 'PID_1')
        self.params['type'] = "PID_Controller"
        self.params['setpoint'] = float(os.getenv("SETPOINT", '293.15'))
        # reverse mode can be activated by passing negative tunings to controller
        self.params['Kp'] = float(os.getenv("KP", '1.0'))
        self.params['Ki'] = float(os.getenv("KI", '0'))
        self.params['Kd'] = float(os.getenv("KD", '0'))
        self.params['lim_low'] = float(os.getenv("LIM_LOW", '0'))
        self.params['lim_upper'] = float(os.getenv("LIM_UPPER", '100'))
        self.params['pause_time'] = float(os.getenv("PAUSE_TIME", 0.2))
        self.params['sensor_entity_name'] = os.getenv("SENSOR_ENTITY_NAME", '')
        self.params['sensor_type'] = os.getenv("SENSOR_TYPE", None)
        self.params['sensor_attr'] = os.getenv("SENSOR_ATTR", '')
        self.params['actuator_entity_name'] = os.getenv("ACTUATOR_ENTITY_NAME", '')
        self.params['actuator_type'] = os.getenv("ACTUATOR_TYPE", '')
        self.params['actuator_command'] = os.getenv("ACTUATOR_COMMAND", '')
        self.params['actuator_command_value'] = self.params['actuator_command'] + '_info'
        self.params['service'] = os.getenv("FIWARE_SERVICE", '')
        self.params['service_path'] = os.getenv("FIWARE_SERVICE_PATH", '')
        self.params['cb_url'] = os.getenv("CB_URL", "http://localhost:1026")

        # settings for security mode
        self.security_mode = os.getenv("SECURITY_MODE", 'False').lower() in ('true', '1', 'yes')
        self.params['token'] = (None, None)
        # Get token from keycloak in security mode
        if self.security_mode:
            self.kp = KeycloakPython()
            self.params['token'] = self.kp.get_access_token()

        # Create simple pid instance
        self.pid = PID(self.params['Kp'], self.params['Ki'], self.params['Kd'],
                       setpoint=self.params['setpoint'],
                       output_limits=(self.params['lim_low'], self.params['lim_upper'])
                       )

        # Additional parameters
        self.auto_mode = True
        self.y = None
        self.x_act = self.params['setpoint']  # set the initial measurement to set point

        # Create the fiware header
        fiware_header = FiwareHeader(service=self.params['service'], service_path=self.params['service_path'])

        # Create orion context broker client
        self.ORION_CB = ContextBrokerClient(url=self.params['cb_url'], fiware_header=fiware_header)

    def create_entity(self):
        """Creates entitiy of PID controller in orion context broker"""
        try:
            self.ORION_CB.get_entity(entity_id=self.params['controller_name'],
                                     entity_type=self.params['type'])
            print('Entity name already assigned')
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise  # throw other errors except "entity not found"
            print('[INFO]: Create new PID entity')
            pid_entity = ContextEntity(id=f"{self.params['controller_name']}",
                                       type=self.params['type'])
            cb_attrs = []
            for attr in ['Kp', 'Ki', 'Kd', 'lim_low', 'lim_upper', 'setpoint']:
                cb_attrs.append(NamedContextAttribute(name=attr,
                                                      type="Number",
                                                      value=self.params[attr]))
            pid_entity.add_attributes(attrs=cb_attrs)
            self.ORION_CB.post_entity(entity=pid_entity, update=True)

    def update_params(self):
        """Read PID parameters of entity in context broker and updates PID control parameters"""
        # read PID parameters from context broker
        for attr in ['Kp', 'Ki', 'Kd', 'lim_low', 'lim_upper', 'setpoint']:
            self.params[attr] = float(
                self.ORION_CB.get_attribute_value(entity_id=self.params['controller_name'],
                                                  entity_type=self.params['type'],
                                                  attr_name=attr))
        # update PID parameters
        self.pid.tunings = (self.params['Kp'], self.params['Ki'], self.params['Kd'])
        self.pid.output_limits = (self.params['lim_low'], self.params['lim_upper'])
        self.pid.setpoint = self.params['setpoint']
        # read measured values from CB
        try:
            # read the current actuator value (synchronize the value with the actuator)
            self.y = self.ORION_CB.get_attribute_value(entity_id=self.params['actuator_entity_name'],
                                                       entity_type=self.params['actuator_type'],
                                                       attr_name=self.params['actuator_command_value'])
            if not isinstance(self.y, (int, float)):
                self.y = None

            # read the value of process variable from sensor
            x = self.ORION_CB.get_attribute_value(entity_id=self.params['sensor_entity_name'],
                                                  entity_type=self.params['sensor_type'],
                                                  attr_name=self.params['sensor_attr'])
            # set 0 if empty
            if x == " ":
                x = '0'
            # convert to float
            self.x_act = float(x)
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.auto_mode = False
            print("Controller connection fails")
        else:
            # If no errors are raised
            self.auto_mode = True

        # Update the actual actuator value to allow warm star after interruption
        self.pid.set_auto_mode(self.auto_mode, last_output=self.y)

    def run(self):
        """Calculation of PID output"""
        try:
            if self.auto_mode:  # if connection is good, auto_mode = True -> controller active
                # calculate PID output
                self.y = self.pid(self.x_act)
                # build command
                command = NamedCommand(name=self.params['actuator_command'], value=round(self.y, 3))
                self.ORION_CB.post_command(entity_id=self.params['actuator_entity_name'],
                                           entity_type=self.params['actuator_type'],
                                           command=command)
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.auto_mode = False
            print("Controller connection fails")

    def update_token(self):
        """
        Update the token if necessary. Write the latest token into the
        header of CB client.
        """
        token = self.kp.check_update_token_validity(input_token=self.params['token'], min_valid_time=60)
        if all(token):  # if a valid token is returned
            self.params['token'] = token
        # Update the header with token
        self.ORION_CB.headers.update(
            {"Authorization": f"Bearer {self.params['token'][0]}"}
        )

    def control_loop(self):
        """The control loop"""
        try:
            while True:
                # Update token if run in security mode
                if self.security_mode:
                    self.update_token()
                else:
                    pass
                self.update_params()
                self.run()
                time.sleep(self.params['pause_time'])
        finally:
            print("control loop fails")
            os.abort()


if __name__ == "__main__":
    pid_controller = Control()
    pid_controller.create_entity()
    pid_controller.control_loop()
