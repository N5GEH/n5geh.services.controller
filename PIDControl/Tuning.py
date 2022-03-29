import time
import numpy as np


class PIDTuning:
    def __init__(self,
                 history_dict: dict = None,
                 u_0: float = None,
                 delta_u: float = None,
                 stable_time: float = None):
        """
        Tune the PID control parameters based on the results of an
        open-loop step response

        Parameters
        ----------
        history_dict: dict
            Dictionary of the historical data from QuantumLeapClient of FiLiP
        u_0: float
            Start point of the control variable
        delta_u: float
            Step width of the control variable
        stable_time: float
            Stable time (from experiment start till makes step,
            and from making step till experiment ends)
        """
        # Get the timestamps and values from the history dict
        self.history_dict = history_dict
        times_dt = self.history_dict["index"]  # elements are datetime objects
        values_raw = self.history_dict["attributes"][0]["values"]
        times_raw = [time.mktime(d.timetuple()) + d.microsecond/1e6 for d in times_dt]

        # Drop values with the same time stamp
        self.times, indices = np.unique(times_raw, return_index=True)  # time has the format of float64
        self.values = [values_raw[i] for i in indices]
        assert len(self.times) == len(self.values)
        slopes = [0] + [(self.values[i+1]-self.values[i]) / (self.times[i+1]-self.times[i])
                        for i in range(len(self.times)-1)]
        self.slopes = slopes

        # Calculate the static gain K
        t_start = self.times[0] + stable_time  # the start time of step
        self.t_start = t_start
        index_start = self.nearest(self.times, t_start)
        delta_y = self.values[-1] - self.values[index_start]
        self.K = delta_y / delta_u

        # Calculate the velocity gain Kv
        slope_steep = max(slopes)  # Find the point with the steepest slope
        index_steep = slopes.index(slope_steep)
        self.Kv = slope_steep / delta_u

        # Calculate the delay L
        time_steep = self.times[index_steep]
        self.L = (time_steep - t_start) -\
                 (self.values[index_steep] - self.values[index_start]) / slope_steep

        # Calculate time constant T
        value_63 = 0.63 * (self.values[-1] - self.values[index_start]) + self.values[index_start]
        index_63 = self.nearest(self.values, value_63)
        time_63 = self.times[index_63]
        self.T = time_63 - t_start - self.L

        print(f"K {self.K}, Kv {self.Kv}, L {self.L}, T {self.T}", flush=True)

    # def tuning_sanchis(self):
    #     """
    #     PI controller tuning procedure of Sanchis et al. [1]
    #     [1] https://doi.org/10.1016/j.isatra.2021.09.008
    #
    #     Returns
    #     -------
    #     list
    #         The three tuning parameters
    #
    #     """
    #     kp = 1
    #     ki = 0
    #     kd = 0
    #     return kp, ki, kd

    def tuning_haegglund(self):
        """
        PI controller tuning procedure of T. Haegglund et al. [2]
        [2] https://doi.org/10.1111/j.1934-6093.2002.tb00076.x

        Returns
        -------
        list
            The three tuning parameters

        """
        def kp_formular():
            _kp = 1
            if self.L < self.T/6:
                _kp = 0.35 / (self.Kv * self.L) - 0.6/self.K
            elif self.L < self.T:
                _kp = 0.25 * self.T / (self.K * self.L)
            elif self.L > self.T:
                _kp = 0.1 * self.T / (self.K * self.L) + 0.15 / self.K
            return _kp

        def ti_formular():
            _ti = 1e6
            if self.L < 0.11*self.T:
                _ti = 7 * self.L
            elif self.L < self.T:
                _ti = 0.8 * self.T
            elif self.L > self.T:
                _ti = 0.3*self.L + 0.5*self.T
            return _ti

        kp = kp_formular()
        ti = ti_formular()
        ki = kp / ti
        kd = 0
        return kp, ki, kd

    def tuning_chien(self, mode: str = "PI"):
        """
        PID controller tuning procedure of Chien et al. [3]. The sugggested parameters
        for "Führung" is used.

        [3] Kun Li Chien, J. A. Hrones, J. B. Reswick: On the Automatic Control of Generalized Passive Systems.
        In: Transactions of the American Society of Mechanical Engineers., Bd. 74, Cambridge (Mass.), USA,
        Feb. 1952, S. 175–185

        Parameters
        ----------
        mode: str
            The mode of the controller, e.g. "P"/"PI"/"PID"

        Returns
        -------
        list
            The three tuning parameters

        """
        assert self.L / self.T < 1/3, "Time delay L must smaller than 1/3 of the time constant T"
        kp = 0
        ki = 0
        kd = 0
        if mode == "P":
            kp = 0.3 * self.T / self.K / self.L
        elif mode == "PI":
            kp = 0.35 * self.T / self.K / self.L
            ti = 1.2 * self.L
            ki = kp / ti
        elif mode == "PID":
            kp = 0.6 * self.T / self.K / self.L
            ti = 1 * self.L
            td = 0.5 * self.L
            ki = kp / ti
            kd = kp * td
        else:
            raise ValueError("mode must be either 'P', 'PI', or 'PID'")
        return kp, ki, kd

    @staticmethod
    def nearest(iterable: [list, tuple], value: float):
        """
        Find the nearest element of an iterable object.

        Parameters
        ----------
        iterable: iterable
        value: numeric

        Returns
        -------
        int
            The index of the found element

        """
        temp = [abs(v - value) for v in iterable]
        index_nearest = temp.index(min(temp))
        return index_nearest

