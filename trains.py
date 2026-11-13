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
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from zeep import Client, Settings, xsd
from zeep.plugins import HistoryPlugin
from zeep.transports import Transport

from config import SmartClockConfig

logger = logging.getLogger(__name__)

WSDL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01"


@dataclass(slots=True)
class TrainDeparture:
    std: str
    destination: str
    etd: str
    platform: str = ""


class TrainGetter:
    """Fetches live departure board data from National Rail OpenLDBWS."""

    def __init__(self, config: SmartClockConfig) -> None:
        self.settings = Settings(strict=False)
        self.history = HistoryPlugin()
        self.transport = Transport(timeout=10, operation_timeout=10)
        self.client: Client | None = None

        header = xsd.Element(
            "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
            xsd.ComplexType(
                [
                    xsd.Element(
                        "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}TokenValue",
                        xsd.String(),
                    ),
                ]
            ),
        )
        self.header_value = header(TokenValue=config.get_train_api_key())
        self.config = config

    def get_trains(self) -> Any:
        if self.client is None:
            self.client = Client(
                wsdl=WSDL,
                settings=self.settings,
                transport=self.transport,
                plugins=[self.history],
            )
        home_crs, _ = self.config.get_train_stations()
        return self.client.service.GetDepartureBoard(
            numRows=20,
            crs=home_crs,
            _soapheaders=[self.header_value],
        )


class _TrainWorker(QThread):
    finished_trains = pyqtSignal(str, list, str)

    def __init__(self, getter: TrainGetter, destination_filter: str) -> None:
        super().__init__()
        self.getter = getter
        self.destination_filter = destination_filter

    def run(self) -> None:
        try:
            res = self.getter.get_trains()
            location_name = getattr(res, "locationName", "Unknown Station")
            departures: list[TrainDeparture] = []

            train_services = getattr(res, "trainServices", None)
            services = getattr(train_services, "service", None) or []

            for t in services:
                dest_locations = getattr(getattr(t, "destination", None), "location", None) or []
                if not dest_locations:
                    continue
                dest_name = getattr(dest_locations[0], "locationName", "")
                if not self.destination_filter or dest_name == self.destination_filter:
                    departures.append(
                        TrainDeparture(
                            std=getattr(t, "std", "--:--"),
                            destination=dest_name,
                            etd=getattr(t, "etd", "Unknown"),
                            platform=getattr(t, "platform", "") or "",
                        )
                    )

            self.finished_trains.emit(location_name, departures, "")
        except Exception as e:
            logger.error("Failed to fetch train departures: %s", e)
            self.finished_trains.emit("", [], str(e))


class TrainManager(QObject):
    """Coordinates live train departure updates in background threads."""

    def __init__(
        self,
        config: SmartClockConfig,
        trains_header_label: QtWidgets.QLabel,
        trains_layout: QtWidgets.QVBoxLayout,
    ) -> None:
        super().__init__()
        self.client = TrainGetter(config)
        self.trainsHeaderLabel = trains_header_label
        self.train_widgets: list[QtWidgets.QWidget] = []
        self.config = config
        self.trainsLayout = trains_layout
        self._worker: _TrainWorker | None = None

        self.trainsLayout.setAlignment(Qt.AlignTop)
        self.trainsLayout.setSpacing(10)

    def update(self, current_time: datetime, is_visible: bool) -> None:
        if current_time.time().second == 0 and is_visible:
            self.update_train_status()

    def update_train_status(self) -> None:
        """Fetch and update train departures asynchronously."""
        if self._worker is not None and self._worker.isRunning():
            return

        home, dest = self.config.get_train_stations()
        self.trainsHeaderLabel.setText(f"Trains from {home} to {dest} (Refreshing...)")

        self._worker = _TrainWorker(self.client, dest)
        self._worker.finished_trains.connect(self._on_trains_ready)
        self._worker.start()

    def _clear_widgets(self) -> None:
        for widget in self.train_widgets:
            self.trainsLayout.removeWidget(widget)
            widget.deleteLater()
        self.train_widgets.clear()

    def _on_trains_ready(
        self, location_name: str, departures: list[TrainDeparture], error: str
    ) -> None:
        now_str = datetime.now().strftime("%H:%M:%S")
        self._clear_widgets()

        if error:
            self.trainsHeaderLabel.setText(f"Trains  •  Error @ {now_str}")
            err_label = QtWidgets.QLabel(f"Unable to fetch train departures: {error}")
            err_label.setWordWrap(True)
            err_label.setStyleSheet("color: #f87171; font-size: 16px; padding: 12px;")
            self.trainsLayout.addWidget(err_label)
            self.train_widgets.append(err_label)
            return

        self.trainsHeaderLabel.setText(
            f"Trains from {location_name}  •  Updated {now_str}"
        )

        if not departures:
            _, dest = self.config.get_train_stations()
            empty_label = QtWidgets.QLabel(
                f"No upcoming departures found for {dest}."
            )
            empty_label.setStyleSheet("color: #94a3b8; font-size: 16px; padding: 12px;")
            self.trainsLayout.addWidget(empty_label)
            self.train_widgets.append(empty_label)
            return

        for dep in departures:
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #1e293b; border: 1px solid #334155; "
                "border-radius: 10px; }"
            )
            row = QtWidgets.QHBoxLayout(card)
            row.setContentsMargins(16, 10, 16, 10)
            row.setSpacing(16)

            time_lbl = QtWidgets.QLabel(dep.std)
            font_time = QFont("Sans Serif", 18)
            font_time.setBold(True)
            time_lbl.setFont(font_time)
            time_lbl.setStyleSheet(
                "border: none; background: transparent; color: #38bdf8; padding: 0;"
            )
            time_lbl.setMinimumWidth(85)

            dest_text = dep.destination
            if dep.platform:
                dest_text += f"  (Plat {dep.platform})"
            dest_lbl = QtWidgets.QLabel(dest_text)
            font_dest = QFont("Sans Serif", 16)
            font_dest.setBold(True)
            dest_lbl.setFont(font_dest)
            dest_lbl.setStyleSheet(
                "border: none; background: transparent; color: #f8fafc; padding: 0;"
            )

            etd_lbl = QtWidgets.QLabel(dep.etd)
            font_etd = QFont("Sans Serif", 16)
            font_etd.setBold(True)
            etd_lbl.setFont(font_etd)
            etd_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            etd_color = (
                "#4ade80"
                if dep.etd.lower() == "on time"
                else "#f87171"
                if "cancel" in dep.etd.lower() or "delay" in dep.etd.lower()
                else "#fbbf24"
            )
            etd_lbl.setStyleSheet(
                f"border: none; background: transparent; color: {etd_color}; padding: 0;"
            )

            row.addWidget(time_lbl)
            row.addWidget(dest_lbl, stretch=1)
            row.addWidget(etd_lbl)

            self.trainsLayout.addWidget(card)
            self.train_widgets.append(card)


def main() -> None:
    client = TrainGetter(SmartClockConfig("config.toml"))
    res = client.get_trains()

    print(f"Trains at {res.locationName}")
    print("=" * 79)

    train_services = getattr(res, "trainServices", None)
    services = getattr(train_services, "service", None) or []

    for t in services:
        print(f"{t.std} to {t.destination.location[0].locationName} - {t.etd}")


if __name__ == "__main__":
    main()
