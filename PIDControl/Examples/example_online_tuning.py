"""
# # Example: Tune the parameters of pid4fiware online.

# Procedure:
    1. Run this script to start the simulation
    2. Open Grafana to visualize the room temperature
    3. Tune the controller parameters in panel


"""

from simulation_main import simulation


if __name__ == '__main__':
    # Simulation with small time step to allow online tuning
    simulation(
        TEMPERATURE_MAX=10,  # maximal ambient temperature
        TEMPERATURE_MIN=-5,  # minimal ambient temperature
        TEMPERATURE_ZONE_START=10,  # start value of the zone temperature
        T_SIM_START=0,  # simulation start time in seconds
        T_SIM_END=24 * 60 * 60,  # simulation end time in seconds
        COM_STEP=60*2,  # 5 seconds communication step
        SLEEP_TIME=0.5  # sleep 0.5 second between every simulation step
    )
