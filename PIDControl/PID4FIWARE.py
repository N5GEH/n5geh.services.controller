# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

Updated on Tue Mar 15 15:47:00 2022

@author: jdu

PID controller with Fiware interface & Web-based controller panel
"""

import time
import os
from simple_pid import PID
import requests
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.context import NamedCommand, ContextEntity, NamedContextAttribute
# import signal
import threading
import sys
import PySimpleGUIWeb as sg
from keycloak_token_handler.keycloak_python import KeycloakPython


class Control:
    """PID controller with FIWARE interface"""

    def __init__(self):
        """Initialization"""

        # use envirnment variables  
        os.environ["CONFIG_FILE"] = "False"

        # define parameters
        self.params = {}
        self.params['name'] = os.getenv("NAME", 'PID_1')
        # TODO hard coded 'type'?
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
        # TODO multiple attributes allowed? If not, why not use the term SENSOR_ATTR without S
        self.params['sensor_attrs'] = os.getenv("SENSOR_ATTRS", '')
        self.params['actuator_entity_name'] = os.getenv("ACTUATOR_ENTITY_NAME", '')
        self.params['actuator_type'] = os.getenv("ACTUATOR_TYPE", '')
        self.params['actuator_command'] = os.getenv("ACTUATOR_COMMAND", '')
        self.params['actuator_command_value'] = self.params['actuator_command'] + '_info'
        # TODO the service and service path has to be the same as the sensor and actuator
        #  (there is only one fiware header!!!)
        self.params['service'] = os.getenv("FIWARE_SERVICE", '')
        self.params['service_path'] = os.getenv("FIWARE_SERVICE_PATH", '')
        self.params['cb_url'] = os.getenv("CB_URL", "http://localhost:1026")

        # settings for security mode
        self.security_mode = os.getenv("SECURITY_MODE", 'False').lower() in ('true', '1', 'yes')
        self.params['token'] = (None, None)  # TODO if it is correct
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
            # TODO better entity name method? To avoid duplicated names
            #  For example: heater(actuator_device)_pid(algorithms)_controller_1(random_number?)
            # TODO entity type is now hard coded to PID_Controller
            pid_entity = ContextEntity(id=f'{self.params["name"]}',
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
        # that means it is possible to change the parameters via context broker
        for attr in ['Kp', 'Ki', 'Kd', 'lim_low', 'lim_upper', 'setpoint']:
            self.params[attr] = float(
                self.ORION_CB.get_attribute_value(entity_id=self.params['name'],
                                                  entity_type=self.params['type'],
                                                  attr_name=attr))
        # update PID parameters
        self.pid.tunings = (self.params['Kp'], self.params['Ki'], self.params['Kd'])
        self.pid.output_limits = (self.params['lim_low'], self.params['lim_upper'])
        self.pid.setpoint = self.params['setpoint']

        # TODO it is possible to use NGSI-LD for fiware intern data transfer @sbl
        #   In this way, the controller does not need to query the values from Sensors
        #   or Actuators. The measurements will be sent to the controller entity, and
        #   the controller here only needs to query data from its own entity.
        # read measured values from CB
        try:
            # read the current actuator value (synchronize the value with the actuator)
            self.y = self.ORION_CB.get_attribute_value(entity_id=self.params['actuator_entity_name'],
                                                       entity_type=self.params['actuator_type'],
                                                       attr_name=self.params['actuator_command_value'])
            if not isinstance(self.y, (int, float)):
                self.y = None

            # read the control value from sensor
            x = self.ORION_CB.get_attribute_value(entity_id=self.params['sensor_entity_name'],
                                                  attr_name=self.params['sensor_attrs'])
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
            # TODO self.auto_mode can also be used to shut down the controller
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


class ControllerPanel:
    def __init__(self):
        # initialize controller parameters (in dict)
        self.params = self.initialize_params()

        # FIWARE parameters
        self.cb_url = os.getenv("CB_URL", "http://localhost:1026")
        self.entity_id = os.getenv("NAME", 'PID_1')
        # TODO hard coded?
        self.entity_type = "PID_Controller"
        self.service = os.getenv("FIWARE_SERVICE", '')
        self.service_path = os.getenv("FIWARE_SERVICE_PATH", '')

        # Create the fiware header
        fiware_header = FiwareHeader(service=self.service, service_path=self.service_path)

        # Create orion context broker client
        self.ORION_CB = ContextBrokerClient(url=self.cb_url, fiware_header=fiware_header)

        # initialize gui window
        sg.theme("DarkBlue")
        param_bars = [
            [sg.Text(param.capitalize(), size=(10, 1)), sg.InputText(self.params[param], key=param)]
            for param in self.params.keys()
        ]
        layout = param_bars + [[sg.Button("Send"), sg.Button("Read")]]
        # layout = [
        #     [sg.Text("Kp:", size=(10, 1)), sg.InputText(self.params["kp"], key="kp")],
        #     [sg.Text("Ki:", size=(10, 1)), sg.InputText(self.params["ki"], key="ki")],
        #     [sg.Text("Kd:", size=(10, 1)), sg.InputText(self.params["kd"], key="kd")],
        #     [sg.Text("Lim_low:", size=(10, 1)), sg.InputText(self.params["lim_low"], key="lim_low")],
        #     [sg.Text("Lim_upper:", size=(10, 1)), sg.InputText(self.params["lim_upper"], key="lim_upper")],
        #     [sg.Text("Setpoint", size=(10, 1)), sg.InputText(self.params["setpoint"], key="setpoint")],
        #     [sg.Button("Send"), sg.Button("Read")],
        # ]
        # TODO use port 80 right now
        self.window = sg.Window("PID controller", layout, web_port=80, web_start_browser=True)

    def gui_update(self):
        for param in self.params.keys():
            self.window[param].update(self.params[param])

    def gui_loop(self):
        try:
            while True:
                event, values = self.window.read(timeout=10)

                if event in (sg.WINDOW_CLOSED, None):
                    break
                elif event == "Send":
                    self.send(values)
                elif event == "Read":
                    print("Read", flush=True)
                    self.read()
        finally:
            print("panel loop fails")
            self.window.close()
            os.abort()

    def read(self):
        try:
            params_update = self.initialize_params()
            for param in self.params.keys():
                params_update[param] = float(self.ORION_CB.get_attribute_value(entity_id=self.entity_id,
                                                                               entity_type=self.entity_type,
                                                                               attr_name=param))
            self.params = params_update
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            print("Cannot find controller entity")
            self.params = self.initialize_params()
        finally:
            self.gui_update()

    def send(self, params):
        for param in self.params.keys():
            try:
                value = float(params[param])
                self.ORION_CB.update_attribute_value(entity_id=self.entity_id,
                                                     entity_type=self.entity_type,
                                                     attr_name=param,
                                                     value=value)
            except ValueError:
                print(f"Wrong value type of {param}: {params[param]}. Must be numeric!")

    @staticmethod
    def initialize_params():
        # initialize controller parameters shown on panel
        params = {
            "Kp": "Proportional gain",
            "Ki": "Integral gain",
            "Kd": "Derivative gain",
            "lim_low": "Lower limit of output",
            "lim_upper": "Upper limit of output",
            "setpoint": "The set point of control variable"
        }
        return params


# def exit_handler(*args):
#     # TODO not used yet
#     pid_controller.ORION_CB.delete_entity(entity_id=pid_controller.params['name'],
#                                           entity_type=pid_controller.params['type'])
#     print("Entity deleted")
#     sys.exit(0)

if __name__ == "__main__":
    # TODO additional environment variable to activate/deactivate front end
    pid_controller = Control()
    pid_controller.create_entity()
    panel = ControllerPanel()
    # panel.gui_setup()

    # # TODO maybe delete the entity if the program is shut down
    # # Delete the controller entity before the container stops
    # signal.signal(signal.SIGTERM, exit_handler)

    # Parallelism with multi thread
    th1 = threading.Thread(target=pid_controller.control_loop, daemon=False)
    th2 = threading.Thread(target=panel.gui_loop, daemon=False)
    th1.start()
    th2.start()

    # Delete controller entity before program is terminated
    # try: ...
    # finally:
    #     # Delete the controller entity if the container stops
    #     exit_handler()
    #     raise
