#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2020  Raphael Kriegl

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

# TODO
#   - werte für magnetschritte und so parse als kommaseparierte liste oder ranges mit start:stop:step oder kombination für ausreißerwerte
#       -> als custom lineedit?

from PySide2.QtCore import Signal, Slot, Qt

class MeasurementControl:
    def __init__(self, parent=None) -> None:
        pass
