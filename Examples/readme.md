# Examples of PID4FIWARE

Here are two examples that can help you get familiar with PID4Fiware.

## Prerequisites

- Docker

    [Docker](https://www.docker.com/) has to be installed on your local machine.

- n5geh plattform

    You must have access to a [n5geh plattform](https://github.com/N5GEH/n5geh.platform), which can be hosted on your local machine or somewhere else. For these examples, it is recommended that you host a platform on your local machine.

- Python

    Python 3 must be installed on your local machine because these examples are all written in python scripts. Besides, the developed library [FiLiP](https://github.com/N5GEH/FiLiP) must be installed.

## Starting Services

Before starting up the services here, you need to ensure that the n5geh platform is running and you have access to it. If you host the platform on your local machine, you do not need to adjust the parameter settings of these examples. Otherwise, you will have to first change the environment parameters in `~\n5geh.services.controller\PIDControl\docker-compose.yml`, e.g. the URL of context broker `CB_URL`. For details about each parameter, please check [here](https://github.com/N5GEH/n5geh.services.controller/tree/master/PIDControl) and look into the docker-compose file.

The controller services can be managed by the bash script `service` provided within this repository. The controller services can be created and then started with:

```bash
./service create
./service start
```

> **NOTE:** If the service is not executable, use `chmod 744 service` change the right

If everything goes well, you should see two running containers right now.

<img src="../Figures/Example_Containers.png" alt="Two runing containers" width="300"/>

> **NOTE:** `service` invoke the `PIDControl/docker-compose.yml`, which is only designed to simplify the settings of these examples. For normal use, please refer to the instruction [here](https://github.com/N5GEH/n5geh.services.controller/tree/master/PIDControl).

## Example 1: Control a Virtual Thermal Zone with PID4FIWARE

In this example, a thermal zone is simulated by the model in `simulation_model.py`, which mainly contains three components: an ambiance, a thermal zone, and an electrical heater (variable heating power). The simulation is conducted in `simulation_main.py`, which sends the data of the simulated thermal zone to the n5geh platform. The information of each device can be viewed in `devices.json`.

This example aims to demonstrate the basic functionality of PID4FIWARE. Therefore, the thermal zone will be simulated twice under the same condition. In the first simulation, the heating power is fixed to 2 KW, while in the second one, the heating power should be controlled by PID4FIWARE.

Run `example_thermal_zone_control.py` to start the simulations. You will receive a hint that asks you to turn off the controller. You can turn if off on Docker Desktop or in command line with:

```bash
./service stop
```

<img src="../Figures/Shutdown_Controller.png" alt="Turn off the controller" width="300"/>

Then you can continue with the first simulation. After that, you will be required to turn on the controller again.

```bash
./service start
```

When the simulation is finished, the results are illustrated just as follows. It can be seen that PID4FIWARE did make a change to the virtual thermal zone.

<img src="../Figures/Example_Result.png" alt="Example Results" width="400"/>

As the next step, you may open the GUI control [panel](http://localhost:80) to simulate with different control parameters. Feel free to explore more!

> **NOTE:** The GUI control panel reads/updates the control parameters on the n5geh platform. Therefore, this is not the only way but a convenient way to change the control parameters.

## Example 2: Tune the Control Parameters Manually

This example is based on the same simulation model as the last one but uses a much slower simulation time. It will take more than two hours to complete the whole simulation, which allows live monitoring of the virtual zone temperature. Therefore a real tuning process of the control parameters can also be imitated in this example.

Run `example_online_tuning.py` to start the simulation. The n5geh platform provides a monitoring tool Grafana to visualize time series data. If you host the n5geh platform on your local machine, Grafana can be accessed [here](http://localhost:3001/) (Username: "admin", password: "admin", by the first login).

After logging in, a `PostgreSQL` datasource must be set up [here](http://localhost:3003/datasources) with the following values.

- **Name:** Controller (an arbitrary name)
- **Host:** crate:5432 (crate is the host name of CrateDB inside the docker network, 5432 is an internal open port for SQL query)
- **Database:** mtcontroller (mt + fiware service name)
- **User:** crate
- **SSL Mode:** disable


<img src="../Figures/Grafana_datasource.png" alt="Data source settings in Grafana" width="300"/>

Then you need to configure a dashboard to visualize the data. A configuration for this example can be loaded by importing `Grafana_Template.json` [here](http://localhost:3001/dashboard/import).

> **NOTE:** If the above settings may not work correctly, please view the information in CrateDB (http://HOSTNAME:4200/#!/tables/) and then adjust the settings in Grafana.

Now you should be able to monitor the live change of the zone temperature and the heating power just like below.

<img src="../Figures/Grafana_Dashboard.png" alt="Live monitoring in Grafana" width="600"/>

You can now open the control [panel](http://localhost:80) and use your expertise with the PID controller to tune the control parameters!
