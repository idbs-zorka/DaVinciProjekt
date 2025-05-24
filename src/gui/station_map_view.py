from PySide6.QtCore import Qt, QObject, Slot, QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtQuickWidgets import QQuickWidget
from pathlib import Path

class MapViewBackend(QObject):

    #               latitude, longitude, id
    addStation = Signal(float, float, int)
    setPosition = Signal(float, float)
    resetIndexes = Signal()
    #                   station_id, index_value
    initIndexValue = Signal(int, int)

    stationSelected = Signal(int)
    @Slot(int)
    def on_station_selected(self,station_id: int):
        self.stationSelected.emit(station_id)

    requestStationIndexValue = Signal(int)
    @Slot(int)
    def request_station_index_value(self,station_id: int):
        print(f"Request station index value: {station_id}")
        self.requestStationIndexValue.emit(station_id)


class StationMapViewWidget(QWebEngineView):

    backend = MapViewBackend()

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        map_path = Path(__file__).with_name("station_map_view.html").resolve()

        self.settings().setAttribute(self.settings().WebAttribute.LocalContentCanAccessRemoteUrls,True)
        self.load(QUrl.fromLocalFile(map_path))
        self.channel = QWebChannel()
        self.channel.registerObject("backend",self.backend)
        self.page().setWebChannel(self.channel)

        self.markerClicked = self.backend.stationSelected
        self.requestStationIndexValue = self.backend.requestStationIndexValue

    def add_station(self,lat: float,lng:float,station_id: int):
        self.backend.addStation.emit(lat,lng,station_id)

    def reset_indexes(self):
        self.backend.resetIndexes.emit()

    def set_position(self,lat: float,lng: float):
        self.backend.setPosition.emit(lat,lng)

    @Slot(int,int)
    def init_index_value(self,station_id: int,value: int):
        print("Init")
        self.backend.initIndexValue.emit(station_id,value)