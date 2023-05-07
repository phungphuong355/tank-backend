# region modules

from matplotlib.gridspec import GridSpec
import NAM_func as nm
import objectivefunctions as obj
import numpy as np
import matplotlib.pyplot as plt
import math
import pandas as pd
import os
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import seaborn
from scipy import stats
from matplotlib.offsetbox import AnchoredText
from scipy import stats
import matplotlib.dates as mdates
import logging


logging.basicConfig(
    format='%(levelname)s: %(module)s.%(funcName)s(): %(message)s')
pd.plotting.register_matplotlib_converters()
seaborn.set()
# plt.style.use('ggplot')
np.seterr(all='ignore')

# endregion


class Nam(object):
    _dir = r'D:\DRIVE\TUBITAK\Hydro_Model\Data\Darbogaz'
    _data = "Darbogaz.csv"

    def __init__(self, Filename: str, Area: int, Cal: bool, DeltaT=24):
        self._working_directory = None
        self.Data_file = None
        self.df = None
        self.P = None
        self.T = None
        self.E = None
        self.Qobs = None
        self.area = Area / (3.6 * DeltaT)
        self.Area = Area
        self.deltat = DeltaT
        self.Spinoff = 0
        self.parameters = None
        # self.initial = np.array([10, 100, 0.5, 500, 10, 0.5, 0.5, 0, 2000, 2.15,2])
        self.initial = np.array(
            [0.97, 721.56, 0.18, 495.91, 25.16, 0.97, 0.11, 0.19, 1121.74, 2.31, 3.51])
        # self.initial_cond = np.array([0.00000000e+000, 1.99000000e+000, 1.58456192e+002, 1.26923570e-118,
        #                              2.62324388e-116, 1.55632958e-027, 6.89606866e-026, 2.86092828e-002])  # Cakit
        # self.initial_cond = np.array([0.00000000e+000, 4.53000000e+000, 2.49773939e+001, 3.76454099e-316,
        #                              2.048395556e-313, 4.61605869e-225, 1.76222522e-222, 2.75755005e-002])  # Darboğaz
        # self.initial_cond = np.array([0.00000000e+00, 9.70000000e-01, 1.89641611e+02, 4.80927311e-03,
        #                              2.95656043e-03, 0.00000000e+00, 0.00000000e+00, 1.39839812e-01])  # Alihoca
        self.States = None
        self.Qsim = None
        self.Lsoil = None
        self.n = None
        self.Date = None
        # Min - Max
        self.bounds = ((0.01, 50), (0.01, 1000), (0.01, 1), (200, 1000), (10, 50),
                       (0.01, 0.99), (0.01, 0.99), (0.01, 0.99), (500, 5000), (0, 4), (-2, 4))
        self.NSE = None
        self.RMSE = None
        self.PBIAS = None
        self.Cal = Cal
        self.statistics = None
        self.export = f'{Filename}.nam.csv'
        self.Sm = None
        self.Ssnow = None
        self.Qsnow = None
        self.Qinter = None
        self.Eeal = None
        self.Qof = None
        self.Qg = None
        self.Qbf = None
        self.usoil = None
        self.flowduration = None

    @property
    def process_path(self):
        return self._working_directory

    @process_path.setter
    def process_path(self, value):
        self._working_directory = value
        pass

    def DataRead(self):
        self.df = pd.read_csv(self.Data_file, sep=',',
                              parse_dates=[0], header=0)
        self.df = self.df.set_index('Date')

    def InitData(self):
        self.P = self.df.P
        self.T = self.df.Temp
        self.E = self.df.E
        self.Qobs = self.df.Q
        self.n = self.df.__len__()
        self.Qsim = np.zeros(self.n)
        self.Lsoil = np.zeros(self.n)
        self.Date = self.df.index

    def nash(self, qobserved, qsimulated):
        if len(qobserved) == len(qsimulated):
            s, e = np.array(qobserved), np.array(qsimulated)
            # s,e=simulation,evaluation
            mean_observed = np.nanmean(e)
            # compute numerator and denominator
            numerator = np.nansum((e - s) ** 2)
            denominator = np.nansum((e - mean_observed) ** 2)
            # compute coefficient
            return 1 - (numerator / denominator)

        else:
            logging.warning(
                "evaluation and simulation lists does not have the same length.")
            return np.nan

    def Objective(self, x):
        self.Qsim, self.Lsoil, self.usoil, self.Ssnow, self.Qsnow, self.Qinter, self.Eeal, self.Qof, self.Qg, self.Qbf = nm.NAM(
            x, self.P, self.T, self.E, self.area, self.deltat, self.Spinoff)
        n = math.sqrt((sum((self.Qsim - self.Qobs) ** 2)) / len(self.Qobs))
        # n = obj.nashsutcliffe(self.Qobs, self.Qsim)
        return n

    def run(self):
        self.InitData()
        if self.Cal == True:
            self.parameters = minimize(self.Objective, self.initial, method='SLSQP', bounds=self.bounds,
                                       options={'maxiter': 1e8, 'disp': True})
            self.Qsim, self.Lsoil, self.usoil, self.Ssnow, self.Qsnow, self.Qinter, self.Eeal, self.Qof, self.Qg, self.Qbf = nm.NAM(
                self.parameters.x, self.P, self.T, self.E, self.area, self.deltat, self.Spinoff)
            print(self.parameters.x)
        else:
            self.Qsim, self.Lsoil, self.usoil, self.Ssnow, self.Qsnow, self.Qinter, self.Eeal, self.Qof, self.Qg, self.Qbf = nm.NAM(
                self.initial, self.P, self.T, self.E, self.area, self.deltat, self.Spinoff)

    def update(self):
        self.df['Qsim'] = self.Qsim
        self.df['Lsoil'] = self.Lsoil
        self.df.to_csv(os.path.join(self.process_path,
                       self.export), index=True, header=True)

    def stats(self):
        mean = np.mean(self.Qobs)
        mean2 = np.mean(self.Qsim)
        self.NSE = 1 - (sum((self.Qsim - self.Qobs) ** 2) /
                        sum((self.Qobs - mean) ** 2))
        self.RMSE = np.sqrt(sum((self.Qsim - self.Qobs) ** 2) / len(self.Qsim))
        self.PBIAS = (sum(self.Qobs - self.Qsim) / sum(self.Qobs)) * 100
        self.statistics = obj.calculate_all_functions(self.Qobs, self.Qsim)

    def interpolation(self):
        fit = np.polyfit(self.Qobs, self.Qsim, 1)
        fit_fn = np.poly1d(fit)
        return fit_fn

    def draw(self):
        self.stats()
        fit = self.interpolation()
        Qfit = fit(self.Qobs)
        width = 15  # Figure width
        height = 10  # Figure height
        f = plt.figure(figsize=(width, height))
        widths = [2, 2, 2]
        heights = [2, 3, 1]
        gs = GridSpec(3, 3, figure=f, width_ratios=widths,
                      height_ratios=heights)
        ax1 = f.add_subplot(gs[1, :])
        ax2 = f.add_subplot(gs[0, :], sharex=ax1)
        ax3 = f.add_subplot(gs[-1, 0])
        ax4 = f.add_subplot(gs[-1, -1])
        ax5 = f.add_subplot(gs[-1, -2])
        color = 'tab:blue'
        ax2.set_ylabel('Precipitation ,mm ', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=13)
        ax2.bar(self.Date, self.df.P, color=color,
                align='center', alpha=0.6, width=1)
        ax2.tick_params(axis='y', labelcolor=color)
        # ax2.set_ylim(0, max(self.df.P) * 1.1, )
        ax2.set_ylim(max(self.df.P) * 1.1, 0)
        ax2.legend(['Precipitation'])
        color = 'tab:red'
        ax2.set_title('NAM Simulation', style='italic',
                      fontweight='bold', fontsize=16)
        ax1.set_ylabel(r'Discharge m$^3$/s', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=13)
        ax1.plot(self.Date, self.Qobs, 'b-', self.Date,
                 self.Qsim, 'r--', linewidth=2.0)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.tick_params(axis='x', labelrotation=45)
        ax1.set_xlabel('Date', style='italic',
                       fontweight='bold', labelpad=20, fontsize=13)
        ax1.legend(('Observed Run-off', 'Simulated Run-off'), loc=2)
        plt.setp(ax2.get_xticklabels(), visible=False)
        anchored_text = AnchoredText("NSE = %.2f\nRMSE = %0.2f\nPBIAS = %0.2f" % (self.NSE, self.RMSE, self.PBIAS),
                                     loc=1, prop=dict(size=11))
        ax1.add_artist(anchored_text)
        # plt.subplots_adjust(hspace=0.05)
        ax3.set_title('Flow Duration Curve', fontsize=11, style='italic')
        ax3.set_yscale("log")
        ax3.set_ylabel(r'Discharge m$^3$/s', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        ax3.set_xlabel('Percentage Exceedence (%)', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax3.legend(['Precipitation'])
        ax3.plot(self.flowdur(self.Qsim)[0], self.flowdur(self.Qsim)[
                 1], 'b-', self.flowdur(self.Qobs)[0], self.flowdur(self.Qobs)[1], 'r--')
        # ax3.plot(self.flowdur(self.Qobs)[0], self.flowdur(self.Qobs)[1])
        ax3.legend(('Observed', 'Simulated'),
                   loc="upper right", prop=dict(size=7))

        plt.grid(True, which="minor", ls="-")

        st = stats.linregress(self.Qobs, self.Qsim)
        # ax4.set_yscale("log")
        # ax4.set_xscale("log")
        ax4.set_title('Regression Analysis', fontsize=11, style='italic')
        ax4.set_ylabel(r'Simulated', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        ax4.set_xlabel('Observed', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        anchored_text = AnchoredText("y = %.2f\n$R^2$ = %0.2f" % (
            st[0], (st[2]) ** 2), loc=4, prop=dict(size=7))
        # ax4.plot(self.Qobs, fit(self.Qsim), '--k')
        # ax4.scatter(self.Qsim, self.Qobs)
        ax4.plot(self.Qobs, self.Qsim, 'bo', self.Qobs, Qfit, '--k')
        ax4.add_artist(anchored_text)

        self.update()
        dfh = self.df.resample('M').mean()
        Date = dfh.index.to_pydatetime()
        ax5.set_title('Monthly Mean', fontsize=11, style='italic')
        ax5.set_ylabel(r'Discharge m$^3$/s', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=9)
        # ax5.set_xlabel('Date', style='italic', fontweight='bold', labelpad=20, fontsize=9)
        ax5.tick_params(axis='y', labelcolor=color)
        ax5.tick_params(axis='x', labelrotation=45)
        # ax5.set_xlabel('Date', style='italic', fontweight='bold', labelpad=20, fontsize=9)
        ax5.legend(('Observed', 'Simulated'), loc="upper right")
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax5.tick_params(axis='x', labelsize=9)
        ax5.plot(Date, dfh.Q, 'b-', Date, dfh.Qsim, 'r--', linewidth=2.0)
        ax5.legend(('Observed', 'Simulated'), prop={'size': 7}, loc=1)
        # ax5.plot(dfh.Q)
        # ax5.plot(dfh.Qsim)
        # ax5.legend()
        plt.grid(True, which="minor", ls="-")

        plt.subplots_adjust(hspace=0.03)
        f.tight_layout()
        plt.show()

    def flowdur(self, x):
        exceedence = np.arange(1., len(np.array(x)) + 1) / len(np.array(x))
        exceedence *= 100
        sort = np.sort(x, axis=0)[::-1]
        low_percentile = np.percentile(sort, 5, axis=0)
        high_percentile = np.percentile(sort, 95, axis=0)
        return exceedence, sort, low_percentile, high_percentile

    def drawflow(self):
        f = plt.figure(figsize=(15, 10))
        ax = f.add_subplot(111)
        # fig, ax = plt.subplots(1, 1)
        ax.set_yscale("log")
        ax.set_ylabel(r'Discharge m$^3$/s', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        ax.set_xlabel('Percentage Exceedence (%)', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax.plot(self.flowdur(self.Qsim)[0], self.flowdur(self.Qsim)[1])
        ax.plot(self.flowdur(self.Qobs)[0], self.flowdur(self.Qobs)[1])
        plt.grid(True, which="minor", ls="-")
        # ax.fill_between(exceedence, low_percentile, high_percentile)
        # plt.show()
        return ax

    def drawscatter(self):
        f = plt.figure(figsize=(15, 10))
        ax = f.add_subplot(111)
        ax.set_yscale("log")
        ax.set_xscale("log")
        ax.set_ylabel(r'Discharge m$^3$/s', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        ax.set_xlabel('Percentage Exceedence (%)', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        ax.scatter(self.Qsim, self.Qobs)
        plt.show()


# Initilize object
# Nam = Nam(Area=1500, Cal=True)

# Process path
# Nam.process_path = r'./'

# Data file
# Nam.Data_file = os.path.join(Nam.process_path, "Tank-data.csv")

# Run NAM
# Nam.run()
# Nam.draw()
# Nam.update()
# Nam.drawflow()
# Nam.drawscatter()
