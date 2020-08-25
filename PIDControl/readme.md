## PIDcontroller.py
The python script `PIDcontroller.py` contains a simple implementation of a PID controller.
The controller can be run in a real time application. Therefore, the parameter *fixed_dt*
has to be zero. Every time the PID controller is exectued, the system time is from the current and last execution is used to calculate 
the integral and derivative part.

If the parameter *fixed_dt* is larger than 0, *fixed_dt* is used as time interval to calculate the integral and derivative part.
This option can be used for simulations.

## PID4FIWARE
The python script `PID4FIWARE.py` includes the PIDcontroller and uses the Filip library to exchange data with the orion context broker.
The needed parameters e.g. URL of the context broker are passed via environment variables.
Additionally, the entity name and the attribute name of the sensor device as well 
as the entity name and the command name of the actuator device have to be specified by environment variables.

The PID controller (proportional-integral-derivative controller) is commonly used in automation to control SISO (Single Input, Single Output) systems. The PID controller varies the control variable (e.g. a valve opening or heating power) to reduce the error between the process variable (e.g. volume flow or temperature) and a set point. 

The PID Controller Service is a PID controller that is virtualized in a docker container (www.docker.com) and integrated in the developed cloud framework (5 Platform Services). The PID Controller Service gets measured values from the orion context broker and send commands to the context broker which are passed to the IoT devices (actuators) afterwards. Therefore, the service name, orion host URL, fiware servicepath and entity names IoT devices for measurement and actuation have to be defined. This is done by environment variables when the container is started. Further, the parameters for the PID controller (e.g. set point) can be defined by environment variables (see below).

In order to manage the PID controller and modify the parameters during operation, the service automatically creates an entity in the orion context broker including the following attributes:


*    setpoint (set point for controller)
*    kp (Kp tuner parameter of PID)
*    ti (Ti tuner parameter of PID)
*    td (Td tuner parameter of PID)
*    lim_low (lower limit of actuator signal)
*    lim_high (higher limit of actuator signal)
*    reverse_act (reverse action, e.g. for cooling instead of heating)


The attributes can be changed by sending a post to the context broker for the specific pid controller service name and attribute (see orion).

A tutorial of the PID Controller Service can be found here: [Tutorial Monitoring and PID Controller](https://git.rwth-aachen.de/EBC/Team_BA/projects/n5geh/services/n5geh.services.controller/-/tree/master/Tutorial)

The PID controller service is available in the docker registry: TODO

Environment variables of the container:

*    NAME (name of the entity created in the context broker for managing the parameters)
*    ORION_HOST (URL to orion context broker)
*    FIWARE_SERVICE (fiware service of sensor and actuator IoT device)
*    FIWARE_SERVICE_PATH (fiware service of sensor and actuator IoT device)
*    SENSOR_ENTITY_NAME (name of the entity that receives the measured data (process variable)))
*    SENSOR_ATTRS (attribute name of the sensor entity that receives the measured data (process variable)))
*    ACTUATOR_ENTITY_NAME (name of the entity corresponding to the actuator)
*    ACTUATOR_TYPE (type of the actuator entity)
*    ACTUATOR_COMMAND (name of the command that corresponds to the control variable)
*    SETPOINT (set point for controller)
*    KP (Kp tuner parameter of PID)
*    TI (Ti tuner parameter of PID)
*    TD (Td tuner parameter of PID)
*    LIM_LOW (lower limit of actuator signal)
*    LIM_HIGH (higher limit of actuator signal)
*    REVERSE_ACT (reverse action, e.g. for cooling instead of heating)
*    PAUSE_TIME (execution interval in seconds: output is computed and send once each interval)

Additional information can be found [here](https://wiki.n5geh.de/pages/viewpage.action?spaceKey=EN&title=PID+Controller+Service)

## Docker files
The `Dockerfile` can be used to create the image of the PID controller. 
Therefore, the filip library has to be copied into this folder (the folder where the two PID scripts and the Dockerfile is).
The `docker-compose.yaml` can be used to run the docker image. The environment variables of the compose file have to be modified according (entity name, url, ...).

