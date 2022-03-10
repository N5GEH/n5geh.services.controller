# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

PID controller with Fiware interface
"""

import time
import os
import PIDcontroller
from simple_pid import PID
import requests

from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.context import NamedCommand, ContextEntity, NamedContextAttribute


# TODO
#  1. how to let controller state pending (if the sensor fails)
#     shut down the controller and keep the container alive? or just let the container die?
#  2. how to tune the control parameters during run time? The parameters can be change by sending requests to CB.
#     Maybe another container?
#  3. write a small tutorial in this
#  4. switch to simple-pid
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
        self.params['Kp'] = float(os.getenv("KP", '1.0'))
        self.params['Ti'] = float(os.getenv("TI", '100'))
        self.params['Td'] = float(os.getenv("TD", '0'))
        self.params['lim_low'] = float(os.getenv("LIM_LOW", '0'))
        self.params['lim_high'] = float(os.getenv("LIM_HIGH", '100'))
        # TODO remove this parameter? reverse mode can be activate by passing negative tunings to controller
        self.params['reverse_act'] = 'True' if os.getenv("REVERSE_ACT", 'False') == 'True' or \
                                               os.getenv("REVERSE_ACT", 'False') == 'true' or \
                                               os.getenv("REVERSE_ACT", 'False') == 'TRUE' \
                                            else 'False'
        self.params['pause_time'] = float(os.getenv("PAUSE_TIME", 0.2))
        self.params['sensor_entity_name'] = os.getenv("SENSOR_ENTITY_NAME", '')
        # TODO multiple attributes allowed? If not, why not use the term attr
        self.params['sensor_attrs'] = os.getenv("SENSOR_ATTRS", '')
        self.params['actuator_entity_name'] = os.getenv("ACTUATOR_ENTITY_NAME", '')
        self.params['actuator_type'] = os.getenv("ACTUATOR_TYPE", '')
        self.params['actuator_command'] = os.getenv("ACTUATOR_COMMAND", '')
        self.params['config_Filip'] = ''  # dummy value
        # TODO new params, check if we need it all
        self.params['service'] = os.getenv("FIWARE_SERVICE", '')
        self.params['service_path'] = os.getenv("FIWARE_SERVICE_PATH", '')
        self.params['cb_url'] = os.getenv("CB_URL", "http://localhost:1026")
        self.params['iota_url'] = os.getenv("IOTA_URL", "http://localhost:4041")

        # PID controller setup
        self.PID = PIDcontroller.PID(self.params['Kp'],
                                     self.params['Ti'],
                                     self.params['Td'],
                                     self.params['lim_low'],
                                     self.params['lim_high'],
                                     self.params['reverse_act'])
        # simple pid instance
        # TODO use the reverse for the tuning parameters, or change the env parameters to Ki and Kd
        self.pid = PID(self.params['Kp'], self.params['Ti'], self.params['Td'],
                       setpoint=self.params['setpoint'],
                       sample_time=self.params['pause_time'],
                       output_limits=(self.params['lim_low'], self.params['lim_high'])
                       )


        # Create the header
        fiware_header = FiwareHeader(service=self.params['service'], service_path=self.params['service_path'])

        # Create orion object
        self.ORION_CB = ContextBrokerClient(url=self.params['cb_url'], fiware_header=fiware_header)
        print(f"cb url: {self.params['cb_url']} \nheaders: {fiware_header}")
        # self.IOTA = IoTAClient(url=self.params['cb_url'], fiware_header=fiware_header)

    def create_entity(self):
        """Creates entitiy of PID controller in orion context broker"""
        # TODO we communicate via 1026, how to change the parameters of the controller
        try:
            self.ORION_CB.get_entity(entity_id=self.params['name'],
                                     entity_type=self.params['type'])
            print('Entity name already assigned')
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            print('[INFO]: Create new PID entity')
            # TODO better way to deal with and entity name?
            #  For example: heater(actuator_device)_pid(algorithms)_controller_1(random_number?)
            # TODO entity type is now hard coded to PID_Controller
            pid_entity = ContextEntity(id=f'{self.params["name"]}',
                                type=self.params['type'])
            cb_attrs = []
            for attr in ['Kp', 'Ti', 'Td', 'lim_low', 'lim_high', 'setpoint']:
                cb_attrs.append(NamedContextAttribute(name=attr,
                                                      type="Number",
                                                      value=self.params[attr]))
            # print(f"create entity, reverse act: {self.params['reverse_act']}")
            cb_attrs.append(NamedContextAttribute(name="reverse_act",
                                                  type="Text",
                                                  value=self.params["reverse_act"]))
            pid_entity.add_attributes(attrs=cb_attrs)
            self.ORION_CB.post_entity(entity=pid_entity, update=True)

    def update_params(self):
        """Read PID parameters of entity in context broker and updates PID control parameters"""

        # read parameters from context broker
        # TODO if the request fails, shut down the controller and keep the container alive? or just let the container die?
        for attr in ['Kp', 'Ti', 'Td', 'lim_low', 'lim_high', 'setpoint']:
            self.params[attr] = float(
                self.ORION_CB.get_attribute_value(entity_id=self.params['name'],
                                                  entity_type=self.params['type'],
                                                  attr_name=attr))
        self.params['reverse_act'] = str(
            self.ORION_CB.get_attribute_value(entity_id=self.params['name'],
                                              entity_type=self.params['type'],
                                              attr_name='reverse_act'))
        # TODO The output here is '0'. Check out if we need to handle "reverse_act" separately
        print(f"reverse_act = ({self.params['reverse_act']})")

        # update PID parameters
        # self.PID.Kp = self.params['Kp']
        # self.PID.Ti = self.params['Ti']
        # self.PID.Td = self.params['Td']
        # self.PID.lim_low = self.params['lim_low']
        # self.PID.lim_high = self.params['lim_high']
        # # TODO how to deal with this parameters, remove it?
        # self.PID.reverse_act = bool(int(self.params['reverse_act']))
        self.pid.tunings = (self.params['Kp'], self.params['Ti'], self.params['Td'])
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
        x = self.ORION_CB.get_attribute_value(entity_id=self.params['sensor_entity_name'],
                                              attr_name=self.params['sensor_attrs'])
        # set 0 if empty
        # TODO check the x value here
        print(f"attribute value of the sensor: x=({x})")
        if x == '" "':
            x = '0'
        # convert to float
        self.x_act = float(x)
        # calculate PID output
        print(f"x_act ={self.x_act}, x_set = {self.params['setpoint']}")
        # self.y = self.PID.run(x_act=self.x_act, x_set=self.params['setpoint'])
        self.y = self.pid(self.x_act)
        # build command
        command = NamedCommand(name=self.params['actuator_command'], value=round(self.y, 3))
        # send post command
        # self.ORION_CB.post_cmd_v1(self.params['actuator_entity_name'],
        #                           self.params['actuator_type'],
        #                           self.params['actuator_command'], round(self.y, 3))
        self.ORION_CB.post_command(entity_id=self.params['actuator_entity_name'],
                                   entity_type=self.params['actuator_type'],
                                   command=command)
        print(f"output: {self.y}")


if __name__ == "__main__":
    pid_controller = Control()
    pid_controller.create_entity()
    while True:
        pid_controller.update_params()
        pid_controller.run()
        # TODO the sample time is also passed to the pid instance, do we really need to pass it twice? or only here?
        time.sleep(pid_controller.params['pause_time'])
