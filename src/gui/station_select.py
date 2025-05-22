from typing import Sequence

from PySide6.QtCore import QTranslator, Signal, Slot, Qt
from PySide6.QtWidgets import QWidget, QLineEdit, QComboBox, QFormLayout, QListWidget, QVBoxLayout, QHBoxLayout, \
    QListWidgetItem

from src.database.views import StationListView
from src.repository import Repository
from dataclasses import dataclass

from src.fuzzy_seach import fuzzy_search

from src.gui.mapview import MapViewWidget

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
        self.city_choice = QComboBox(self)
        self.city_choice.addItems(["Wybierz miasto", *cities])
        self.city_choice.currentIndexChanged.connect(self.on_city_changed)

        self.layout = QFormLayout(self)

        self.layout.addRow(self.tr("Szukaj"),self.search_query_input)
        self.layout.addRow(self.tr("Miasto"),self.city_choice)

    def current_city(self):
        return self.city_choice.currentText() if self.city_choice.currentIndex() > 0 else None

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


class StationSelectWidget(QWidget):
    select_filter_widget: StationSelectFilter

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

        self.stations_list_widget.clear()
        self.stations_list_widget.addItems([station.name for station in self.filtered_stations])

    def __init__(self,repository: Repository, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setMinimumSize(800,400)
        self.layout = QHBoxLayout(self)

        self.stations = repository.get_station_list_view()
        self.filtered_stations = self.stations

        cities = list(set((st.city for st in self.stations)))
        cities.sort()

        self.select_filter_widget = StationSelectFilter(parent=self,cities=cities)
        self.select_filter_widget.filter_changed.connect(self.on_filter_changed)

        self.stations_list_widget = QListWidget(self)

        for station in self.stations:
            item = QListWidgetItem(station.name,listview=self.stations_list_widget)
            item.setData(Qt.ItemDataRole.UserRole,station)

        self.stations_list_widget.itemClicked.connect(lambda x: self.on_station_clicked(x.data(Qt.ItemDataRole.UserRole)))

        left = QVBoxLayout()
        left.addWidget(self.select_filter_widget)
        left.addWidget(self.stations_list_widget)

        self.map_view = MapViewWidget(parent=self)
        self.map_view.markerClicked.connect(self.on_station_marker_clicked)
        self.layout.addLayout(left, stretch=0)
        self.layout.addWidget(self.map_view, stretch=1)

    def on_station_clicked(self,station: StationListView):
        self.map_view.add_marker(station.latitude,station.longitude,station.name,'black')

    def on_station_marker_clicked(self,name):
        station = next(station for station in self.stations if station.name == name)
        print(f"Station clicked: {station}")