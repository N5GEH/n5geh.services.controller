# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

Updated on Tue Mar 15 15:47:00 2022

@author: jdu

PID controller with Fiware interface
"""
import time
from abc import ABC
from Controller import Controller4Fiware, logging
from simple_pid import PID
import os


class PID4Fiware(Controller4Fiware, ABC):
    """
    PID controller that interact with Fiware platform.
    """
    def __init__(self):
        path_config = os.path.join(os.getcwd(), "config")
        logging.debug(f"Load config from: {path_config}")
        super().__init__(config_path=path_config)

        # Create simple pid instance
        self.pid = PID(Kp=self.controller_entity.kp.value,
                       Ki=self.controller_entity.ki.value,
                       Kd=self.controller_entity.kd.value,
                       setpoint=self.controller_entity.setpoint.value,
                       output_limits=(self.controller_entity.limLower.value, self.controller_entity.limUpper.value)
                       )

        # create the variables for the pid controller
        self.u = None  # control variable u
        self.limLower = None  # lower limit of u
        self.limUpper = None  # upper limit of u
        self.y_act = None  # actual value of process variable y
        self.y_set = None  # setpoint

    def match_variables(self):
        """
        Match the setpoint and measurement from the controller entity and the sensor entity.
        """
        self.y_act = self.input_entities[0].get_attributes()[0].value
        self.y_set = self.controller_entity.setpoint.value

    def update_pid(self):
        """
        Update the instance of simple_pid controller instance.
        """
        pid_dict = self.controller_entity.dict()

        # Update PID parameters
        self.pid.tunings = (pid_dict['kp']['value'], pid_dict['ki']['value'], pid_dict['kd']['value'])
        self.pid.output_limits = (pid_dict['limLower']['value'], pid_dict['limUpper']['value'])
        self.pid.setpoint = pid_dict['setpoint']['value']

    def control_algorithm(self):
        """
        Calculate PID output.
        """
        # Calculate the output and commands base on the input, controller parameters and external input
        self.u = self.pid(self.y_act)

        # For multiple outputs system, the best practice is to update the value of outputs/commands with following code
        for entity in self.command_entities:
            for _comm in entity.get_attributes():
                # logging.debug(f"calculate command {_comm.name} to id {entity.id} with type {entity.type}")
                _comm.value = self.u
                entity.update_attribute([_comm])

    def control_cycle(self):
        """
        The control cycle of PID controller. Beside the basic structure defined in Controller4Fiware,
        match_variables() and update_pid() are also invoked.
        """
        try:
            while True:
                start_time = time.time()

                # Update token if run in security mode
                if self.security_mode:
                    self.update_token()

                # update the input
                logging.debug("read input")
                self.read_input_variable()

                # update the controller parameters
                logging.debug("read parameters")
                self.read_controller_parameter()

                # match variables
                logging.debug("match")
                self.match_variables()

                # update controller
                self.update_pid()

                # execute only when the controller is activated
                if self.active:
                    # calculate the output and commands
                    logging.debug("algorithm")
                    self.control_algorithm()

                    # send commands
                    logging.debug("send")
                    self.send_commands()

                    # wait until next cycle
                    self.hold_sampling_time(start_time=start_time)
        except Exception as ex:
            logging.error(str(ex))
            raise


if __name__ == '__main__':
    pid_controller = PID4Fiware()
    pid_controller.create_controller_entity()
    pid_controller.control_cycle()
