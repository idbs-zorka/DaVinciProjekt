from dataclasses import dataclass
from typing import Sequence

import logging
from PySide6.QtCore import Signal, Slot, Qt, QTimer, QEventLoop, QThreadPool, QRunnable, QObject
from PySide6.QtWidgets import QWidget, QLineEdit, QComboBox, QFormLayout, QListWidget, QVBoxLayout, QHBoxLayout, \
    QListWidgetItem

from src.config import AQ_TYPES
from src.database.views import StationListView
from src.fuzzy_seach import fuzzy_search
from src.gui.station_map_view import StationMapViewWidget
from src.repository import Repository


def wait_for_signal(signal, timeout=5000):
    """
    Czeka na emisję danego QtSignal.
    Zwraca krotkę argumentów, które sygnał przekazał, lub
    rzuca TimeoutError, jeśli minie `timeout` ms.
    """
    loop = QEventLoop()
    result = []

    def _on_emit(*args):
        result.append(args)
        loop.quit()

    # Podłączamy handler i watchdog co będzie pierwsze
    signal.connect(_on_emit)
    QTimer.singleShot(timeout, loop.quit)

    loop.exec()  # <–– tu wchodzimy w pętlę aż do quit()

    signal.disconnect(_on_emit)
    if result:
        return result[0]       # krotka argumentów
    else:
        raise TimeoutError(f"Sygnał nie został wyemitowany w {timeout} ms")

@dataclass
class FilterState:
    search_query: str
    city: str | None

class StationSelectFilter(QWidget):
    filter_changed = Signal(FilterState)

    def __init__(self,cities: Sequence[str],*args,**kwargs):
        super().__init__()

        self.search_query_input = QLineEdit(self)
        self.search_query_input.textChanged.connect(self.on_search_query_changed)
        self.city_combo = QComboBox(self)
        self.city_combo.addItems(["Wybierz miasto", *cities])
        self.city_combo.currentIndexChanged.connect(self.on_city_changed)

        self.layout = QFormLayout(self) #Tworzenie elemenu: Text:Element

        self.layout.addRow(self.tr("Szukaj"), self.search_query_input)
        self.layout.addRow(self.tr("Miasto"), self.city_combo)

    def current_city(self):
        return self.city_combo.currentText() if self.city_combo.currentIndex() > 0 else None

    @Slot(str)
    def on_search_query_changed(self, text: str):
        self.filter_changed.emit(FilterState(
            search_query=text,
            city=self.current_city()
        ))

    @Slot(int)
    def on_city_changed(self, value: int):
        self.filter_changed.emit(FilterState(
            search_query=self.search_query_input.text(),
            city=self.current_city()
        ))


class StationIndexFetcher(QRunnable):
    class Signals(QObject):
        finished = Signal(int,int)

    def __init__(self,station_id: int,index_type: str,repository: Repository):
        super().__init__()
        self.station_id = station_id
        self.index_type = index_type
        self.repository = repository
        self.signals = self.Signals()

    def run(self):
        own_repository = self.repository.clone()
        value = own_repository.fetch_station_air_quality_index_value(self.station_id,self.index_type)

        if value is None:
             value = -1

        self.signals.finished.emit(self.station_id,value)


class StationSelectWidget(QWidget):

    def __init__(self,repository: Repository, *args,**kwargs):
        self.repository = repository
        self.thread_pool = QThreadPool.globalInstance()

        super().__init__(*args,**kwargs)
        self.setMinimumSize(1200,600)
        self.layout = QHBoxLayout(self)

        self.stations = repository.get_station_list_view()
        self.filtered_stations = self.stations

        cities = list(set((st.city for st in self.stations))) #Utworzenie listy niepowtarzajacych sie miast
        cities.sort()

        self.select_filter_widget = StationSelectFilter(parent=self,cities=cities)
        self.select_filter_widget.filter_changed.connect(self.on_filter_changed)

        self.stations_list_widget = QListWidget(self)

        self.set_station_list_items(self.stations)

        self.stations_list_widget.itemClicked.connect(self.on_station_clicked)

        left = QVBoxLayout()
        left.addWidget(self.select_filter_widget)
        left.addWidget(self.stations_list_widget)


        aq_index_type_form = QFormLayout()

        self.aq_index_type_combo = QComboBox()
        self.aq_index_type_combo.addItems(AQ_TYPES)
        self.aq_index_type_combo.currentIndexChanged.connect(self.on_aq_index_changed)

        aq_index_type_form.addRow("Indeks", self.aq_index_type_combo)

        self.map_view = StationMapViewWidget(parent=self)

        wait_for_signal(self.map_view.loadFinished)

        self.setup_markers()

        self.map_view.markerClicked.connect(self.on_station_marker_clicked)
        self.map_view.requestStationIndexValue.connect(self.on_request_station_index_value)

        right = QVBoxLayout()
        right.addLayout(aq_index_type_form,stretch=0)
        right.addWidget(self.map_view,stretch=1)

        self.layout.addLayout(left, stretch=0)
        self.layout.addLayout(right, stretch=1)

    @Slot(FilterState)
    def on_filter_changed(self,state: FilterState):
        self.filtered_stations = self.stations
        if state.city is not None:
            self.filtered_stations = [
                st for st in self.filtered_stations
                if st.city == state.city
            ]

        if state.search_query != '':
            name_to_station = {
                st.name: st for st in self.filtered_stations
            }
            searched = fuzzy_search(state.search_query,name_to_station.keys(),score_cutoff=60)
            self.filtered_stations = [
            name_to_station[result] for result in searched
            ]
        else:
            self.filtered_stations.sort(key=lambda x: x.name)

        self.set_station_list_items(self.filtered_stations)

    def set_station_list_items(self,stations: list[StationListView]):
        self.stations_list_widget.clear()

        for st in stations:
            item = QListWidgetItem(st.name,listview=self.stations_list_widget)
            item.setData(Qt.ItemDataRole.UserRole,st)

    def setup_markers(self):
        for st in self.stations:
            self.map_view.add_station(st.latitude,st.longitude,st.id)

    @Slot(QListWidgetItem)
    def on_station_clicked(self,item: QListWidgetItem):
        station = item.data(Qt.ItemDataRole.UserRole)
        print(f"Trying to set position: {station}")
        self.map_view.set_position(station.latitude,station.longitude)

    @Slot(int)
    def on_station_marker_clicked(self,station_id: int):
        station = next(station for station in self.stations if station.id == station_id)
        print(f"Station clicked: {station}")


    @Slot(int)
    def on_aq_index_changed(self,index: int):
        self.map_view.reset_indexes()

    @Slot(int)
    def on_request_station_index_value(self,station_id: int):
        current_index = self.aq_index_type_combo.currentText()
        logging.info(f"Requesting index value: {station_id} : {current_index}")

        task = StationIndexFetcher(station_id,current_index,self.repository)
        task.signals.finished.connect(self.map_view.init_index_value)

        self.thread_pool.start(task)
