"""
# # Example: Use pid4fiware to control the temperature of a virtual thermal zone.

# Procedure:
    1. simulate the virtual thermal zone without controller
    2. after a hint, turn on the pid4fiware controller and simulate again
    3. view the visualized results

"""

import matplotlib.pyplot as plt
from simulation_main import simulation


# Main script
if __name__ == '__main__':
    # Give hints to turn off the controller
    input("Turn off the controller, and press ENTER to start the first simulation")

    # Simulation without controller
    history_weather_station, history_zone_temperature_sensor, history_heater_power = \
        simulation(
            TEMPERATURE_MAX=10,  # maximal ambient temperature
            TEMPERATURE_MIN=-5,  # minimal ambient temperature
            TEMPERATURE_ZONE_START=10,  # start value of the zone temperature
            T_SIM_START=0,  # simulation start time in seconds
            T_SIM_END=24 * 60 * 60,  # simulation end time in seconds
            COM_STEP=60 * 15  # 1 min communication step in seconds
        )

    # plot results
    fig1, axs = plt.subplots(2, 1, figsize=(7, 7))

    t_simulation = [item["simtime"] for item in history_weather_station]
    temperature = [item["temperature"] for item in history_weather_station]
    l1 = axs[0].plot(t_simulation, temperature, label="Ambient Temperature")

    t_simulation = [item["simtime"] for item in history_zone_temperature_sensor]
    temperature = [item["temperature"] for item in
                   history_zone_temperature_sensor]
    l2 = axs[0].plot(t_simulation, temperature, label="Zone Temperature")
    axs[0].set_xlabel('time in s')
    axs[0].set_ylabel('temperature in °C')
    axs[0].set_ylim(-6, 30)

    ax2 = axs[0].twinx()
    t_simulation = [item["simtime"] for item in history_heater_power]
    power = [item["heater_power"] for item in history_heater_power]
    # find the index of first numeric element
    index_num = power.index(next(i for i in power if isinstance(i, (int, float))))
    l3 = ax2.plot(t_simulation[index_num:], power[index_num:], ":r", label="Heating Power")
    ax2.set_ylabel('heating power in W')
    ax2.set_ylim(0, 4000)

    lns = l1 + l2 + l3
    labs = [l.get_label() for l in lns]
    axs[0].legend(lns, labs, loc="upper right")
    axs[0].set_title("Simulation results without controller")

    fig1.tight_layout()
    fig1.show()

    # Give hints to turn on the controller
    input("Turn on the controller, and press ENTER to start the second simulation")

    # Simulation with pid4fiware
    history_weather_station, history_zone_temperature_sensor, history_heater_power = \
        simulation(
            TEMPERATURE_MAX=10,  # maximal ambient temperature
            TEMPERATURE_MIN=-5,  # minimal ambient temperature
            TEMPERATURE_ZONE_START=10,  # start value of the zone temperature
            T_SIM_START=0,  # simulation start time in seconds
            T_SIM_END=24 * 60 * 60,  # simulation end time in seconds
            COM_STEP=60 * 15  # 1 min communication step in seconds
        )

    # plot results
    t_simulation = [item["simtime"] for item in history_weather_station]
    temperature = [item["temperature"] for item in history_weather_station]
    l1 = axs[1].plot(t_simulation, temperature, label="Ambient Temperature")

    t_simulation = [item["simtime"] for item in history_zone_temperature_sensor]
    temperature = [item["temperature"] for item in
                   history_zone_temperature_sensor]
    l2 = axs[1].plot(t_simulation, temperature, label="Zone Temperature")
    axs[1].set_xlabel('time in s')
    axs[1].set_ylabel('temperature in °C')
    axs[1].set_ylim(-6, 30)

    ax3 = axs[1].twinx()
    t_simulation = [item["simtime"] for item in history_heater_power]
    power = [item["heater_power"] for item in history_heater_power]
    # find the index of first numeric element
    index_num = power.index(next(i for i in power if isinstance(i, (int, float))))
    l3 = ax3.plot(t_simulation[index_num:], power[index_num:], ":r", label="Heating Power")
    ax3.set_ylabel('heating power in W')
    ax3.set_ylim(0, 4000)

    lns = l1 + l2 + l3
    labs = [l.get_label() for l in lns]
    axs[1].legend(lns, labs, loc="lower right")
    axs[1].set_title("Simulation results with pid controller")

    fig1.tight_layout()
    fig1.show()
