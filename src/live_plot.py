#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2021  Raphael Kriegl

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

import random
import sys
import matplotlib
matplotlib.use('Qt5Agg')

from PySide2.QtCore import QCoreApplication, QRunnable, QThreadPool, QTimer, Slot, Qt
from PySide2.QtWidgets import QVBoxLayout, QWidget
from droplet import Droplet

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

import logging

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class MPLCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = fig.add_subplot(111,autoscale_on=True)
        super(MPLCanvas, self).__init__(fig)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.fn = fn

    @Slot()
    def run(self):
        self.fn(*self.args, **self.kwargs)


class LivePlot(QWidget):

    def __init__(self, parent = None):
        super(LivePlot, self).__init__(parent)

        self.ui : Ui_main = None # set post init bc of parent relationship not automatically applied on creation in generated script
        self._first_show = True

        self.canvas = MPLCanvas(parent=self, width=5, height=4, dpi=100)
        self.canvas.axes.set_xlabel("Time [s]")
        self.canvas.axes.set_ylabel("Angle [rad]")
        self.canvas.axes.grid('on')
        self.canvas.axes.autoscale(enable=True, axis='both')


        self.toolbar = NavigationToolbar2QT(self.canvas,self)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

        self.threadpool = QThreadPool()

        self.tab_visible = False

        n_data = 50
        self.xdata = []
        self.ydata = []

        # We need to store a reference to the plotted line 
        # somewhere, so we can apply the new data to it.
        self._plot_ref = None

        self.show()

        logging.info("initialized live plot")
        

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self.ui = self.window().ui
            self.connect_signals()
            self._first_show = False

    def connect_signals(self):
        self.ui.dataControl.update_plot_signal.connect(self.update_plot)
        self.ui.measurementControl.start_measurement_signal.connect(self.prepare_plot)

    @Slot()
    def prepare_plot(self):
        """prepares the plot

        :param xsize,ysize: expected size of axes
        :param group: grouping column name, defaults to None
        """
        self.ydata = []
        self.xdata = []


    @Slot(float, float)
    def update_plot(self, time, angle):
        """add new point to graph and redraw  
        will start new thread to update the ui
        :param time: time
        :param angle: the droplet angle
        """
        # worker = Worker(self.do_update_plot, time, angle)
        # self.threadpool.start(worker)
        self.do_update_plot(time, angle)

    def do_update_plot(self, time, angle):
        """update plot via thread

        :param data: all the data from the pipeline
        """
        logging.debug("update plot")
        # Drop off the first y element, append a new one.
        self.ydata = self.ydata[:] + [angle]
        self.xdata = self.xdata[:] + [time]

        # Note: we no longer need to clear the axis.       
        # if self._plot_ref is None:
        #     # First time we have no plot reference, so do a normal plot.
        #     # .plot returns a list of line <reference>s, as we're
        #     # only getting one we can take the first element.
        #     plot_refs = self.canvas.axes.plot(self.xdata, self.ydata, 'b')
        #     self._plot_ref = plot_refs[0]
            
        # else:
        #     # We have a reference, we can use it to update the data for that line.
        #     self._plot_ref.set_ydata(self.ydata)
        #     self._plot_ref.set_xdata(self.xdata)

        self.canvas.axes.plot(self.xdata, self.ydata, 'b')

        # Trigger the canvas to update and redraw.
        self.canvas.draw()

    def clear(self):
        pass
