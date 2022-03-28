# Examples of PID4FIWARE

Here are some examples that can help you get familiar with PID4FIWARE.

## Prerequisites

- Docker

    [Docker](https://www.docker.com/) has to be installed on your local machine.

- n5geh plattform

    You must have access to a [n5geh plattform](https://github.com/N5GEH/n5geh.platform), which can either be hosted on your local machine or somewhereelse. For these examples, it is recommanded that you host a plattform on your local machine.

- Python

    Python 3 has to be installed on your local machine, because these examples are all written in python scripts. Besides, the developed library [FiLiP](https://github.com/N5GEH/FiLiP) must be installed.

## Starting Services

Before starting up the services here, you need to make sure that the n5geh plattform is runing and you have access to it. If you host the plattform on your local machine, you do not need to adjust the parameter settings of these examples. Otherwise, you will have to first adjust the environment parameters in `~\n5geh.services.controller\PIDControl\docker-compose.yml`, e.g. the URL of context broker `CB_URL`. For details about each parameter, please view in the docker-compose file.

Then you can change your working directory to `~\n5geh.services.controller\PIDControl` and start the PID4FIWARE and a GUI control panel using `docker compose` command:

```bash
cd \n5geh.services.controller\PIDControl
docker compose up -d
```

If everything goes well, you should see two runing containers right now.

![Two runing containers](../Figures/Example_Containers.png)

> **NOTE:** This `docker-compose.yml` should only be used for setting up these examples. For actual use, please refers to the instruction [here](https://github.com/N5GEH/n5geh.services.controller/tree/master/PIDControl).

## Example 1: Control a Virtual Thermal Zone with PID4FIWARE

In this example, a thermal zone is simulated by the model in `simulation_model.py`, which mainly contains three components: an ambience, a thermal zone, and an electrical heater (variable heating power). The simulation is conducted in `simulation_main.py`, which sends the data of the simulated thermal zone to the n5geh plattform. The information of each device can viewed in `devices.json`.

This example aims to demonstrate the basic functionality of PID4FIWARE. Therefore, the thermal zone will be simulated twice under the same contidion. In first simulation, the heating power is fixed to 2 KW, while in the second one, the heating power should be controlled by PID4FIWARE.

Run `example_thermal_zone_control.py` to start the simulations. You will recieve a hint that tells you to turn off the controller, which can be done with:

```bash
docker stop pid4fiware
```

![Turn off the controller](../Figures/Shutdown_Controller.png)

Then you can continue with the first simulation. After that you will be required to turn on the controller.

```bash
docker start pid4fiware
```

When the simulation is finished, the results are illustrated just as follow. It can be seen that PID4FIWARE did make a change to the virtual thermal zone.

![Example Results](../Figures/Example_Result.png)

As next step, you may open the GUI control [panel](http://localhost:80) to simulate with different control parameters. Feel free to explore more!

> **NOTE:** The GUI control panel simply reads/updates the control parameters on the n5geh plattform. Therefore, this is not the only way but a convinient way to change the control parameters.

## Example 2: Tune the Control Parameters Manually

This example bases on the same simulation model as the last example, but uses a much slower simulation time. It will take more than two hours to complete the whole simulation, which allows a live monitoring of the virtual zone temperature. Therefore a real tuning process of the control parameters can also be imitated in this example.

Run `example_online_tuning.py` to start the simulation. The n5geh plattform provides a monitoring tool Grafana to visualize time series data. If you host the n5geh plattform on your local machine, Grafana can be accessed [here](http://localhost:3001/) (Username: "admin", password: "admin", by first login).

After logging in, a `PostgreSQL` datasource must be set up [here](http://localhost:3003/datasources) with the following values.

![Data source settings in Grafana](../Figures/Grafana_datasource.png)

Then you need to configure a dashboard to visuallize the data. A configuration for this example can be loaded by importing `Grafana_Template.json` [here](http://localhost:3001/dashboard/import).

> **NOTE:** If the above settings may not work properly, please view the information in CrateDB (http://HOSTNAME:4200/#!/tables/) and then adjust the settings in Grafana.

Now you should be able to monitor the live change of the zone tempereature and the heating power just like bellow.

![Live monitoring in Grafana](../Figures/Grafana_Dashboard.png)

You can now open the control [panel](http://localhost:80) and use your expertise with PID controller to tune the contol parameters!
