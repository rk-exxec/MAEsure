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

import logging
from time import sleep
from pumpy import Pump, PumpError, remove_crud

class Microliter(Pump):
    """Create Pump object for Microliter OEM Pump.

    Argument:
        Chain: pump chain

    Optional arguments:
        address: pump address. Default is 0.
        name: used in logging. Default is Pump 11.
    """

    def write(self,command):
        self.serialcon.write(str(self.address + command + '\r').encode())

    def read(self,bytes=5):
        response = self.serialcon.read(bytes).decode().strip()

        if len(response) == 0:
            raise PumpError('%s: no response to command' % self.name)
        else:
            return response

    def readall(self):
        response = ""
        while len(response) == 0:
            sleep(0.2)
            response = self.serialcon.read_all().decode().strip()

        if len(response) == 0:
            raise PumpError('%s: no response to command' % self.name)
        else:
            return response

    def setdiameter(self, diameter):
        """Set syringe diameter (millimetres).

        Pump 11 syringe diameter range is 0.1-35 mm. Note that the pump
        ignores precision greater than 2 decimal places. If more d.p.
        are specificed the diameter will be truncated.
        """
        if diameter > 4.61 or diameter < 0.1:
            raise PumpError('%s: diameter %s mm is out of range' % 
                            (self.name, diameter))
        
        diam_str = remove_crud(str(diameter))

        # Send command   
        self.write('MMD ' + diam_str)
        resp = self.readall()

        # Pump replies with address and status (:, < or >)        
        if (resp[-1] in ":<>*IWDT" or "*" in resp):
            # check if diameter has been set correctlry
            self.write('DIA')
            resp = self.read(15)
            returned_diameter = remove_crud(resp[0:9])
            
            # Check diameter was set accurately
            if float(returned_diameter) != diameter:
                logging.error('%s: set diameter (%s mm) does not match diameter'
                              ' returned by pump (%s mm)', self.name, diam_str,
                              returned_diameter)
            else:
                self.diameter = float(returned_diameter)
                logging.info('%s: diameter set to %s mm', self.name,
                             self.diameter)
        else:
            raise PumpError(f'{self.name}: unknown response to setdiameter: {resp}')

    def setflowrate(self, flowrate):
        """Set flow rate (microlitres per minute).

        The pump will tell you if the specified flow rate is out of
        range. This depends on the syringe diameter. See Pump 11 manual.
        """
        flowrate = remove_crud(str(flowrate))

        self.write('ULM ' + flowrate)
        resp = self.readall()
        self.write('ULMW ' + flowrate)
        resp = self.readall()
        
        if (resp[-1] in ":<>*IWDT" or "*" in resp):
            # Flow rate was sent, check it was set correctly
            self.write('RAT')
            resp = self.readall()
            returned_flowrate = remove_crud(resp[2:8])

            if returned_flowrate != flowrate:
                logging.error('%s: set infuse flowrate (%s uL/min) does not match'
                              'flowrate returned by pump (%s uL/min)',
                              self.name, flowrate, returned_flowrate)
            elif returned_flowrate == flowrate:
                self.flowrate = returned_flowrate
                logging.info('%s: infuse flow rate set to %s uL/min', self.name,
                              self.flowrate)
            self.write('RATW')
            resp = self.readall()
            returned_flowrate = remove_crud(resp[2:8])

            if returned_flowrate != flowrate:
                logging.error('%s: set withdraw flowrate (%s uL/min) does not match'
                              'flowrate returned by pump (%s uL/min)',
                              self.name, flowrate, returned_flowrate)
            elif returned_flowrate == flowrate:
                self.flowrate = returned_flowrate
                logging.info('%s: withdraw flow rate set to %s uL/min', self.name,
                              self.flowrate)
        elif 'OOR' in resp:
            raise PumpError('%s: flow rate (%s uL/min) is out of range' %
                           (self.name, flowrate))
        else:
            raise PumpError(f'{self.name}: unknown response: {resp}')
            
    def infuse(self):
        """Start infusing pump."""
        self.write('RUN')
        resp = self.readall()      
        if resp[-1] != '>':
            raise PumpError(f"Pump did not start infuse!: {resp}")  
        logging.info('%s: infusing',self.name)

    def withdraw(self):
        """Start withdrawing pump."""
        self.write('RUNW')
        resp = self.readall()
        if resp[-1] != '<':
            raise PumpError(f"Pump did not start withdraw!: {resp}")

        logging.info('%s: withdrawing',self.name)

    def stop(self):
        self.write("STP")
        resp = self.readall()
        if not resp[-1] in ":*IWDT":
            raise PumpError(f"Pump did not stop: {resp}")


    def settargetvolume(self, targetvolume):
        """Set the target volume to infuse or withdraw (microlitres)."""
        self.write('CLT')
        resp = self.readall()
        self.write('CLTW')
        resp = self.readall()
        self.write('CLV')
        resp = self.readall()
        self.write('CLVW')
        resp = self.readall()
        self.write('ULT ' + str(targetvolume))
        resp = self.readall()
        self.write('ULTW ' + str(targetvolume))
        resp = self.readall()

        # response should be CRLFXX:, CRLFXX>, CRLFXX< where XX is address
        # Pump11 replies with leading zeros, e.g. 03, but PHD2000 misbehaves and 
        # returns without and gives an extra CR. Use int() to deal with
        if resp[-1] in ":<>*IWDT" or "*" in resp:
            self.targetvolume = float(targetvolume)
            logging.info('%s: target volume set to %s uL', self.name,
                         self.targetvolume)
        else:
            raise PumpError(f'{self.name}: unknown response: {resp}')
