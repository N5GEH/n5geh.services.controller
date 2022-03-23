## PID4FIWARE

The PID controller (proportional-integral-derivative controller) is commonly used in automation to control SISO (Single Input, Single Output) systems. The PID controller adjusts the control variable (e.g. a valve opening or heating power) to minimize the error between the process variable (e.g. volume flow or temperature) and a given setpoint.

PID4FIWARE provides a PID controller service that can control a system via the developed IoT plattform [n5geh](https://github.com/N5GEH/n5geh.platform). PID4FIWARE uses the [FiLiP](https://github.com/N5GEH/FiLiP) library to exchange data with the plattform, i.e. reading measurements from the sensor or sending commands to the actuator. The used PID controller is based on the public libary [simple-pid](https://pypi.org/project/simple-pid/).

In order to manage the PID controller and modify the control parameters during operation, PID4FIWARE automatically creates an entity in the orion context broker of the [n5geh](https://github.com/N5GEH/n5geh.platform) IoT plattform, which holds the following 6 attributes for the PID controller:

| Attribute Name | Description                         |
|----------------|-------------------------------------|
| setpoint       | Setpoint of the process variable    |
| Kp             | Proportional gain of PID            |
| Ki             | Integral gain of PID                |
| Kd             | Deviation gain of PID               |
| lim_low        | Lower limit of the control variable |
| lim_upper      | Upper limit of the control variable |

In other words, the control parameters are storaged on the IoT plattform, which can be adjusted by sending requests to the orioin context broker. It must be addressed that the reverse mode (reverse action, e.g. for cooling instead of heating) can be activated by assigning negative values to Kp, Ki, and Kd.

Besides, in order to take measurements and actuations, the entity name and the attribute name of the sensor device as well as the entity name and the command name of the actuator device have to be defined. These information including the plattform specific information (e.g. context broker url) are passed to PID4FIWARE via environment variables. All the supported environment variables are shown as below.

| Name        | Example Value                     | Descriptions                                               |
|----------------------|-----------------------------------|------------------------------------------------------------|
| CB_URL               | <http://host.docker.internal:1026>  | URL of the orion context broker FROM INSIDE THE CONTAINER! |
| FIWARE_SERVICE       | controller                        | Fiware service name                                        |
| FIWARE_SERVICE_PATH  | /buildings                        | Fiware service path                                        |
| CONTROLLER_NAME      | PID_example                       | Entity ID of the PID controller                            |
| SENSOR_ENTITY_NAME   | urn:ngsi-ld:TemperatureSensor:001 | Entity ID of the sensor device                             |
| SENSOR_TYPE          | TemperatureSensor                 | Entity type of the sensor device                           |
| SENSOR_ATTR          | temperature                       | Attribute name of the process variable                     |
| ACTUATOR_ENTITY_NAME | urn:ngsi-ld:Heater:001            | Entity ID of the actuator device                           |
| ACTUATOR_TYPE        | Heater                            | Entity type of the actuator device                         |
| ACTUATOR_COMMAND     | heater_power                      | Command name of the control variable                       |
| SETPOINT             | 20                                | Setpoint of the process variable                           |
| PAUSE_TIME           | 0.1                               | Sampling time step                                         |
| LIM_LOW              | 0                                 | Lower limit of the control variable                        |
| LIM_UPPER            | 7000                              | Upper limit of the control variable                        |
| KP                   | 200                               | Proportional gain Kp                                       |
| KI                   | 50                                | Integral gain Ki                                      |
| KD                   | 0                                 | Deviation gain Kd                                      |
| SECURITY_MODE        | False                             | Whether to use security mode                               |

PID4FIWARE is virtualized in a [docker](www.docker.com) container. The virtualization makes it very simple to deploy.

The container can either be built and then run locally, or can be pulled directly from docker hub.

The first option is to build an image locally. You need to clone this repository to your local computer or virtual machine (VM) and then change the working directory to `\n5geh.services.controller\PIDControl`:

```bash
git clone https://github.com/N5GEH/n5geh.services.controller.git

cd n5geh.services.controller

cd PIDControl
```

Then you can build the image use `docker build` command:

```bash
docker build --tag pid4fiware .
```

After that, you can run the image `pid4fiware` as a container:

```bash
docker run -d \
    --env-file env.list \
    --volume "$(pwd)/keycloak_token_handler/.env:/app/keycloak_token_handler/.env" \
    --restart always \
    --name pid_controller_1 \
    pid4fiware
```

The second option is to use the online image on docker hub [here](www.dockerhub:pid4fiware.come) (note that this image may not always be updated):

```bash
TODO
docker run -d \
    --env-file env.list \
    --volume "$(pwd)/keycloak_token_handler/.env:/app/keycloak_token_handler/.env" \
    --restart always \
    --name pid_controller_2 \
    dockerhub:pid4fiware
```

The various environment variables are passed to the container through the file `env.list`. Therefore, please make sure to set up each variable properly before starting up PID4FIWARE as a container.

## Control Panel

The control panel is a web based GUI interface of the PID controllers. It simply reads/sends control parameters from the orion context broker and displays the data in a user-friendly way. It must be addressed that this panel is mainly designed for demonstration and learning. It is not recommended to use this panel to interact with the deployed PID-controller in real practice because **there is no guarantee for its reliability and functionality**.

This control panel can also be run as a docker container. Firstly, you should build a local image named `pidpanel`:

```bash
cd control_panel
docker build --tag pidpanel .
```

Secondly, you must adjust the following three enrionment variables in `docker-compose.yml`.

| Name        | Example Value                     | Descriptions                                               |
|----------------------|-----------------------------------|------------------------------------------------------------|
| CB_URL               | <http://host.docker.internal:1026>  | URL of the orion context broker FROM INSIDE THE CONTAINER! |
| FIWARE_SERVICE       | controller                        | Fiware service name                                        |
| FIWARE_SERVICE_PATH  | /buildings                        | Fiware service path                                        |

Finnaly, the container can be simply started by:

```bash
docker compose up -d
```

If you are using the default settings, you can open the control panel [here](http://localhost:80). Now you should see the interface as shown below.

![Web based contol panel GUI](../Figures/control_panel.png)
