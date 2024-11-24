#
# Open Live Departure Boards Web Service (OpenLDBWS) API Demonstrator
# Copyright (C)2018-2024 OpenTrainTimes Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from zeep import Client, Settings, xsd
from zeep.plugins import HistoryPlugin
from config import SmartClockConfig
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont
from datetime import datetime

WSDL = 'http://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01'

class TrainGetter:
    def __init__(self, config: SmartClockConfig):
        settings = Settings(strict=False)

        history = HistoryPlugin()

        self.client = Client(wsdl=WSDL, settings=settings, plugins=[history])

        header = xsd.Element(
            '{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken',
            xsd.ComplexType([
                xsd.Element(
                    '{http://thalesgroup.com/RTTI/2013-11-28/Token/types}TokenValue',
                    xsd.String()),
            ])
        )
        self.header_value = header(TokenValue=config.get_train_api_key())
        self.config = config


    def get_trains(self):
        return self.client.service.GetDepartureBoard(numRows=20, crs=self.config.get_train_stations()[0], _soapheaders=[self.header_value])


class TrainManager():
    def __init__(self, config: SmartClockConfig, trainsHeaderLabel, trainsLayout):
        self.client = TrainGetter(config)
        self.trainsHeaderLabel = trainsHeaderLabel
        self.train_labels = []
        self.config = config
        self.trainsLayout = trainsLayout

    def update(self, current_time, is_visible):
        if current_time.time().second == 0 and is_visible:
            self.update_train_status()

    def update_train_status(self):
        """Update train status"""
        # Get trains
        res = self.client.get_trains()
        # Update header 
        self.trainsHeaderLabel.setText("Trains at " + res.locationName + " -- Updated at " + datetime.now().strftime("%H:%M:%S"))

        # Clear existing status
        for label in self.train_labels:
            label.deleteLater()
        self.train_labels.clear()

        for t in res.trainServices.service:
            if t.destination.location[0].locationName == self.config.get_train_stations()[1]:
                status = t.std + " to " + t.destination.location[0].locationName + " - " + t.etd
                label = QtWidgets.QLabel(status)
                font = QFont('Times', 20)
                font.setBold(True)
                label.setFont(font)
                self.trainsLayout.addWidget(label)
                self.train_labels.append(label)

def main():
    client = TrainGetter(SmartClockConfig('config.toml'))
    res = client.get_trains()

    print("Trains at " + res.locationName)
    print("===============================================================================")

    services = res.trainServices.service

    for t in services:
        print(t.std + " to " + t.destination.location[0].locationName + " - " + t.etd)


if __name__ == "__main__":
    main()