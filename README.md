# Overview

This repository contains controllers that control IoT devices via the FIWARE framework.
Figure 1 illustrates the communication with the fiware framework: The controller service gets the current value of the IoT devices from the orion context broker
and sends commands to the context broker that are passed to the IoT devices afterwards.
The [filip](https://git.rwth-aachen.de/EBC/Team_BA/projects/n5geh/tools/n5geh.tools.filip) library is used for the communication with the orion context broker.


![Overview of the framework and controller integration](Figures/Overview.png)

***Figure 1:*** *Overview of the framework and controller integration (_source_: https://fiware-tutorials.readthedocs.io/en/latest/iot-over-mqtt/index.html)*


# Services

**PIDcontrol service** 

This service includes a PID controller that communiates with the controlled system (IoT devices) via the fiware platfrom.
The controller receives the process variable (measurement) from the context broker with a http get request.
The computed control variable (actuation) is send back to the context broker afterwards and passed as a command to the  IoT device (actuator).


