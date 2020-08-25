# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 14:49:16 2019

@author: aku

PID controller with Fiware interface
"""

import time
import os
import PIDcontroller
import sys

filip_path = os.getenv("FILIP_PATH", '/filip')
sys.path.append(filip_path) # insert correct path to the filip library
import filip.config, filip.orion


class Control():
    """PID controller with FIWARE interface""" 
    
    def __init__(self):
        """Initialization"""
        
        # use envirnment variables  
        os.environ["CONFIG_FILE"] = "False"
          
        # define parameters
        self.params={}
        self.params['name'] = os.getenv("NAME", 'PID_1')
        self.params['setpoint'] = float(os.getenv("SETPOINT", '293.15')) 
        self.params['Kp'] = float(os.getenv("KP", '1.0'))
        self.params['Ti'] = float(os.getenv("TI", '100'))
        self.params['Td'] = float(os.getenv("TD", '0'))
        self.params['lim_low'] = float(os.getenv("LIM_LOW", '0'))
        self.params['lim_high'] = float(os.getenv("LIM_HIGH", '100'))
        self.params['reverse_act'] = 'True' if os.getenv("REVERSE_ACT", 'False') == 'True' or os.getenv("REVERSE_ACT", 'False') == 'true' or os.getenv("REVERSE_ACT", 'False') == 'TRUE' else 'False'
        self.params['pause_time'] = float(os.getenv("PAUSE_TIME", 2))
        self.params['sensor_entity_name'] = os.getenv("SENSOR_ENTITY_NAME", '')
        self.params['sensor_attrs'] = os.getenv("SENSOR_ATTRS", '')
        self.params['actuator_entity_name'] = os.getenv("ACTUATOR_ENTITY_NAME", '')
        self.params['actuator_type'] = os.getenv("ACTUATOR_TYPE", '')
        self.params['actuator_command'] = os.getenv("ACTUATOR_COMMAND", '')
        self.params['config_Filip'] = '' #dummy value
    
        # PID controller setup
        self.PID = PIDcontroller.PID(self.params['Kp'],
                                     self.params['Ti'],
                                     self.params['Td'],
                                     self.params['lim_low'],
                                     self.params['lim_high'],
                                     self.params['reverse_act'])

        # create filip config
        self.CONFIG = filip.config.Config(self.params['config_Filip'])
        # Create orion object
        self.ORION_CB = filip.orion.Orion(self.CONFIG)
        


    def create_entity(self):
        """Creates entitiy of PID controller in orion context broker"""
        
        if self.ORION_CB.get_entity(self.params['name']) is None:
            
            print('[INFO]: Create new PID entity')
            
            entity_dict = {"id":self.params['name'], "type":'PID_controller'}
            for attr in ['Kp', 'Ti', 'Td', 'lim_low', 'lim_high', 'setpoint']:
                entity_dict.update({attr:{'value':self.params[attr],'type':'Number'}})

            entity_dict.update({'reverse_act':{'value':self.params['reverse_act'],'type':'Text'}})
            
            entity = filip.orion.Entity(entity_dict)#, attrs)

            self.ORION_CB.post_entity(entity)
            
        else:
            print('Entity name already assigned')
   
    
    
    def update_params(self):
        """Read PID parameters of entity in context broker and updates PID control parameters"""
        
        # read parameters from context broker
        for attr in ['Kp', 'Ti', 'Td', 'lim_low', 'lim_high', 'setpoint']:
            self.params[attr] = float(self.ORION_CB.get_entity_attribute_value(entity_name=self.params['name'], attribute_name=attr))
        self.params['reverse_act'] = str(self.ORION_CB.get_entity_attribute_value(entity_name=self.params['name'], attribute_name='reverse_act'))    
        
        # update PID parameters
        self.PID.Kp = self.params['Kp']
        self.PID.Ti = self.params['Ti']
        self.PID.Td = self.params['Td']
        self.PID.lim_low = self.params['lim_low']
        self.PID.lim_high = self.params['lim_high']
        self.PID.reverse_act = eval(eval(self.params['reverse_act']))
        
        
        
    def run(self):
        """Calculation of PID output"""
        
        # read sensor value (actual value)
        x = self.ORION_CB.get_entity_attribute_value(entity_name=self.params['sensor_entity_name'],
                                                     attribute_name=self.params['sensor_attrs'])
        # set 0 if empty
        if x == '" "':
            x = '0'
        # convert to float
        self.x_act = float(x)     
        # calculate PID output
        self.y = self.PID.run(x_act = self.x_act, x_set = self.params['setpoint'])
        # send post command
        self.ORION_CB.post_cmd_v1(self.params['actuator_entity_name'], 
                                  self.params['actuator_type'],
                                  self.params['actuator_command'], round(self.y,3))


if __name__ == "__main__":  
    # os.environ["CONFIG_FILE"] = "False"
    # os.environ["ORION_HOST"] = "http://137.226.249.254"
    # os.environ['FIWARE_SERVICE'] = "simple_iot"
    # os.environ['FIWARE_SERVICE_PATH'] = "/"
    # os.environ['SENSOR_ENTITY_NAME'] = "urn:ngsi-ld:Sensor:T1"
    # os.environ['SENSOR_ATTRS'] = "urn:ngsi-ld:Measurement:Temperature"
    # os.environ['ACTUATOR_ENTITY_NAME'] = "urn:ngsi-ld:Actuator:valve1"
    # os.environ['ACTUATOR_TYPE'] = "Actuator"
    # os.environ['ACTUATOR_COMMAND'] = "valveSet"   
    
    PID = Control()
    PID.create_entity()

    
#PID.ORION_CB.update_attribute('PID_rh', 'setpoint', 298.15)  
    while True:
  #  for i in range(100): 
        PID.update_params()
        PID.run()
        time.sleep(PID.params['pause_time']) 