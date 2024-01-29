"""
The framework for controller that interact with FIWARE.
@author: jdu
"""
import json
import os.path
import warnings
from abc import ABC, abstractmethod
import requests
from filip.clients.ngsi_v2 import ContextBrokerClient, QuantumLeapClient
from filip.models.base import FiwareHeader
from filip.models.ngsi_v2.context import NamedCommand, ContextEntity
import time
from keycloak_token_handler.keycloak_python import KeycloakPython
import os
import logging

# Get log level from environment variable, default to INFO if not set
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# Configure logging
logging.basicConfig(level=log_level,
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s')


class Controller4Fiware(ABC):
    """
    Controller4Fiware is an abstract class. It contains several abstract methods, which
    must be implemented in a controller subclass. This script already gives recommended
    structures for these methods.

    There are several TODOs in this script, which indicate the tasks that are required during
    the implementation.

    Please note the following points:
      1. For each type of concrete controller, the input and output structure should be the same
      2. If the number of variables must change, a new controller type should be implemented
      3. The declaration of variables happens in configure files
    """
    def __init__(self, config_path=None):
        """
        Args:
            config_path: the root path of the configuration files
        """
        input_path = os.path.join(config_path, "input.json")
        with open(input_path, "r") as f:
            input_list = json.load(f)
        output_path = os.path.join(config_path, "output.json")
        with open(output_path, "r") as f:
            output_list = json.load(f)
        command_path = os.path.join(config_path, "command.json")
        with open(command_path, "r") as f:
            command_list = json.load(f)
        controller_path = os.path.join(config_path, "controller.json")
        with open(controller_path, "r") as f:
            controller_dict = json.load(f)

        # Config file of the controller must contain the initial value of parameters
        self.controller_entity = ContextEntity.model_validate(controller_dict)
        # TODO check the command entity. All attributes should have the type "command".

        self.input_entities = [ContextEntity.model_validate(entity)
                               for entity in input_list]
        self.output_entities = [ContextEntity.model_validate(entity)
                                for entity in output_list]
        self.command_entities = [ContextEntity.model_validate(entity)
                                 for entity in command_list]

        # TODO define external inputs if any, e.g. temperature forecast
        # self.temp_forecast = None

        self.active = True  # the controller will be deactivated if set to False

        # Read from ENV
        self.sampling_time = float(os.getenv("SAMPLING_TIME", 0.5))
        assert self.sampling_time >= 0.1, "Controller sampling time must be larger than 0.1 sec"
        controller_entity_dict = self.controller_entity.model_dump()
        controller_entity_dict["id"] = os.getenv("CONTROLLER_ENTITY_ID", "urn:ngsi-ld:Controller:001")
        controller_entity_dict["type"] = os.getenv("CONTROLLER_ENTITY_TYPE", "Controller")
        self.controller_entity = ContextEntity(**controller_entity_dict)
        self.fiware_params = dict()
        self.fiware_params["ql_url"] = os.getenv("QL_URL", "http://localhost:8668")
        self.fiware_params["cb_url"] = os.getenv("CB_URL", "http://localhost:1026")
        self.fiware_params["service"] = os.getenv("FIWARE_SERVICE", "controller")
        self.fiware_params["service_path"] = os.getenv("FIWARE_SERVICE_PATH", "/")

        # Create the fiware header
        fiware_header = FiwareHeader(service=self.fiware_params['service'],
                                     service_path=self.fiware_params['service_path'])

        # Create orion context broker client
        s = requests.Session()
        self.ORION_CB = ContextBrokerClient(url=self.fiware_params['cb_url'], fiware_header=fiware_header,
                                            session=s)
        self.QL_CB = QuantumLeapClient(url=self.fiware_params['ql_url'], fiware_header=fiware_header)

        # settings for security mode
        self.security_mode = os.getenv("SECURITY_MODE", 'False').lower() in ('true', '1', 'yes')
        self.token = (None, None)
        # Get token from keycloak in security mode
        if self.security_mode:
            self.kcp = KeycloakPython()
            # Get initial token
            self.token = self.kcp.get_access_token()

    def update_token(self):
        """
        Update the token if necessary. Write the latest token into the
        header of CB client.
        """
        token = self.kcp.check_update_token_validity(input_token=self.token, min_valid_time=60)
        if all(token):  # if a valid token is returned
            self.token = token
        # Update the header with token
        self.ORION_CB.headers.update(
            {"Authorization": f"Bearer {self.token[0]}"})

    def read_controller_parameter(self):
        """
        Read the controller parameters from Fiware platform
        """
        for _param in self.controller_entity.get_attributes():
            # logging.debug(f"read {_param.name} from {self.controller_entity.id} with type {self.controller_entity.type}")
            _param.value = self.ORION_CB.get_attribute_value(entity_id=self.controller_entity.id,
                                                             entity_type=self.controller_entity.type,
                                                             attr_name=_param.name)
            self.controller_entity.update_attribute(attrs=[_param])

    def read_input_variable(self):
        """
        Read input variables from Fiware platform
        """
        try:
            for entity in self.input_entities:
                for _input in entity.get_attributes():
                    # logging.debug(f"read {_input.name} from id {entity.id} and type {entity.type}")
                    _input.value = self.ORION_CB.get_attribute_value(entity_id=entity.id,
                                                                     entity_type=entity.type,
                                                                     attr_name=_input.name)
                    entity.update_attribute(attrs=[_input])
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.active = False
            logging.error(msg)
            logging.error("Input entities/attributes not fond, controller stop")
        else:
            # if no error
            self.active = True

    def send_output_variable(self):
        """
        Send output variables to Fiware platform

        NOTICE: output variables are normal attributes of context entities,
        which will not be forwarded to devices
        """
        try:
            for entity in self.output_entities:
                for _output in entity.get_attributes():
                    # logging.debug(f"update output {_output.name} of id {entity.id} with type {entity.type}")
                    self.ORION_CB.update_attribute_value(entity_id=entity.id,
                                                         attr_name=_output.name,
                                                         value=_output.value,
                                                         entity_type=entity.type)
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.active = False
            logging.error(msg)
            logging.error("Output entities/attributes not fond, controller stop")

    def send_commands(self):
        """
        Send commands to Fiware platform. The commands will be forwarded to the corresponding actuators.
        """
        try:
            for entity in self.command_entities:
                for _comm in entity.get_attributes():
                    # logging.debug(f"send command {_comm.name} to id {entity.id} with type {entity.type}")
                    _comm = NamedCommand(**_comm.dict())
                    self.ORION_CB.post_command(entity_id=entity.id,
                                               entity_type=entity.type,
                                               command=_comm)
        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise
            self.active = False
            logging.error(msg)
            logging.error("Commands  cannot be sent, controller stop")

    def create_controller_entity(self):
        """
        Create the controller entity while starting. The controller parameters and their initial values are
        defined in the config/controller.json. The entity id and entity type of the controller are defined
        in environment variables.
        """
        try:
            controller_entity_exist = self.ORION_CB.get_entity(entity_id=self.controller_entity.id,
                                                               entity_type=self.controller_entity.type)
            logging.warning("Controller entity_id is already assigned")
            # check the structure, extra attributes are allowed
            keys = controller_entity_exist.model_dump().keys()
            for key in self.controller_entity.model_dump().keys():
                if key not in keys:
                    msg = f'The existing entity has a different structure. ' \
                          f'Please delete it or change the id'
                    logging.error(msg)
                    raise NameError(msg)
            else:
                logging.info("The existing entity contains all expected "
                             "attributes")

        except requests.exceptions.HTTPError as err:
            msg = err.args[0]
            if "NOT FOUND" not in msg.upper():
                raise  # throw other errors except "entity not found"
            logging.info("Create new PID entity")
            self.ORION_CB.post_entity(entity=self.controller_entity, update=True)

    def hold_sampling_time(self, start_time: float):
        """
        Wait in each control cycle until the sampling time (or cycle time) is up. If the algorithm takes
        more time than the sampling time, a warning will be given.

        Args:
            start_time:

        """
        if (time.time()-start_time) > self.sampling_time:
            warnings.warn("The processing time is longer than the sampling time. The sampling time must be increased!")
        while (time.time()-start_time) < self.sampling_time:
            time.sleep(0.01)
        else:
            return

    @abstractmethod
    def control_algorithm(self):
        """
        This abstract method must be implemented in subclass.
        The outputs/commands are calculated in this method based on the current values of inputs and parameters.
        """
        # calculate the output and commands base on the input, controller parameters and external input
        ...

        # For MIMO system, the best practice is to update the value of outputs/commands with following code
        for entity in self.command_entities:
            for _comm in entity.get_attributes():
                logging.debug(f"calculate command {_comm.name} to "
                              f"id {entity.id} with type {entity.type}")
                _comm.value = ...  # TODO
                entity.update_attribute([_comm])

        for entity in self.output_entities:
            for _output in entity.get_attributes():
                logging.debug(f"calculate output {_output.name} to "
                              f"id {entity.id} with type {entity.type}")
                _output.value = ...  # TODO
                entity.update_attribute([_output])

    @abstractmethod
    def control_cycle(self):
        """
        This abstract method must be implemented in subclass.
        This abstract method already defines a basic structure of the control cycle. Basically, all the following
        invoked functions/methods should be used. Other functions/methods can also be added in the implementation
        of the subclass.
        """
        try:
            while True:
                start_time = time.time()

                # Update token if run in security mode
                if self.security_mode:
                    self.update_token()

                # update the input
                self.read_input_variable()

                # get external input
                ...  # TODO

                # update the controller parameters
                self.read_controller_parameter()

                # execute only when the controller is activated
                if self.active:
                    # calculate the output and commands
                    self.control_algorithm()

                    # send output
                    self.send_output_variable()

                    # send commands
                    self.send_commands()

                    # wait until next cycle
                    self.hold_sampling_time(start_time=start_time)
        except Exception as ex:
            logging.error(msg=str(ex))
            raise
