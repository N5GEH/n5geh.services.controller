# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 13:57:00 2022

@author: jdu

Web based GUI of controller tuning panel.
"""
import os
import requests
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader
import PySimpleGUIWeb as sg


class ControllerPanel:
    def __init__(self):
        # initialize controller parameters (in dict)
        self.params = self.initialize_params()

        # FIWARE parameters
        self.cb_url = os.getenv("CB_URL", "http://localhost:1026")
        self.entity_id = None  # will be read on the web GUI
        self.entity_type = "PID_Controller"
        self.service = os.getenv("FIWARE_SERVICE", '')
        self.service_path = os.getenv("FIWARE_SERVICE_PATH", '')

        # Create the fiware header
        fiware_header = FiwareHeader(service=self.service, service_path=self.service_path)

        # Create orion context broker client
        self.ORION_CB = ContextBrokerClient(url=self.cb_url, fiware_header=fiware_header)

        # initial pid controller list
        self.controller_list = []
        try:
            self.refresh_list()
        except:
            pass

        # initialize gui window
        sg.theme("DarkBlue")
        pid_id_bar = [
            [sg.Text("Controller ID", size=(10, 1)),
             sg.Combo(self.controller_list, key="controller_list"),
             sg.Button("Refresh")]
        ]
        param_bars = [
            [sg.Text(param.capitalize(), size=(10, 1)), sg.InputText(self.params[param], key=param)]
            for param in self.params.keys()
        ]
        io_bars = [[sg.Button("Send"), sg.Button("Read")]]
        layout = pid_id_bar + param_bars + io_bars
        self.window = sg.Window("PID controller", layout, web_port=80, web_start_browser=True)

    def gui_update(self):
        """Update the shown text on web GUI"""
        # update parameter values
        for param in self.params.keys():
            self.window[param].update(self.params[param])
        self.window["controller_list"].Update(values=self.controller_list)
        self.window["controller_list"].Update(value=self.entity_id)

    def gui_loop(self):
        """GUI main loop"""
        try:
            while True:
                event, values = self.window.read(timeout=1000)
                self.entity_id = values["controller_list"]
                if event in (sg.WINDOW_CLOSED, None):
                    break
                elif event == "Send":
                    self.send(values)
                elif event == "Read":
                    print("Read", flush=True)
                    self.read()
                elif event == "Refresh":
                    self.refresh_list()
                    self.gui_update()
        finally:
            print("panel loop fails")
            self.window.close()
            os.abort()

    def read(self):
        """Read parameter values from context broker"""
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
        """Send new parameter values to context broker"""
        for param in self.params.keys():
            try:
                value = float(params[param])
                self.ORION_CB.update_attribute_value(entity_id=self.entity_id,
                                                     entity_type=self.entity_type,
                                                     attr_name=param,
                                                     value=value)
            except ValueError:
                print(f"Wrong value type of {param}: {params[param]}. Must be numeric!")

    def refresh_list(self):
        """Refresh the controller list"""
        entity_list = self.ORION_CB.get_entity_list(entity_types=[self.entity_type])
        if entity_list:
            list_new = [controller.id for controller in entity_list]
        else:
            list_new = []
        if all([isinstance(controller_id, str) for controller_id in list_new]) or not list_new:
            self.controller_list = list_new

    @staticmethod
    def initialize_params():
        """Initialize the values of all control parameters"""
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


if __name__ == "__main__":
    panel = ControllerPanel()
    panel.gui_loop()
