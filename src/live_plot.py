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

from PySide2.QtCore import QRectF, Slot
from PySide2.QtWidgets import QGraphicsRectItem

import pyqtgraph as pg

import logging

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class LivePlot(pg.PlotWidget):

    def __init__(self, parent = None):
        super(LivePlot, self).__init__(parent=parent)

        self.ui : Ui_main = None # set post init bc of parent relationship not automatically applied on creation in generated script
        self._first_show = True

        pg.setConfigOptions(antialias=True)
        self.xdata = []
        self.ydata = []
        self.plotItem.clear()
        self.plt: pg.PlotDataItem = self.plotItem.plot(y=self.ydata, x=self.xdata)#, symbol='x', symbolPen='y', symbolBrush=0.2)
        self.plt.setPen('y')

        self.setLabel('left', 'Angle', units='°')
        self.setLabel('bottom', 'Time', units='s')
        self.showGrid(x=True, y=True)
        
        self.plt.setData(y=[], x=[])

        self.tab_visible = False
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

        self.ydata = self.ydata[:] + [angle]
        self.xdata = self.xdata[:] + [time]

        self.plt.setData(y=self.ydata, x=self.xdata)

