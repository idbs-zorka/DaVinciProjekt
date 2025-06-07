from pathlib import Path

from PySide6.QtCore import QObject, Slot, QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineLoadingInfo
from PySide6.QtWebEngineWidgets import QWebEngineView


class MapViewBackend(QObject):

    # Python wysyla do mapy
    #               latitude, longitude, id
    addStation = Signal(float, float, int)
    setPosition = Signal(float, float)
    resetIndexes = Signal()
    #                   station_id, index_value
    initIndexValue = Signal(int, int)

    # Mapa wysyla do pythona
    stationSelected = Signal(int)
    @Slot(int)
    def on_station_selected(self,station_id: int):
        self.stationSelected.emit(station_id)

    requestStationIndexValue = Signal(int)
    @Slot(int)
    def request_station_index_value(self,station_id: int):
        print(f"Request station index value: {station_id}")
        self.requestStationIndexValue.emit(station_id)

    leaftletLoaded = Signal()
    @Slot()
    def on_leaflet_load(self):
        self.leaftletLoaded.emit()


class StationMapViewWidget(QWebEngineView):

    backend = MapViewBackend() # Na potrzeby integracji JavaScript

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        map_path = Path(__file__).with_name("station_map_view.html").resolve()

        self.settings().setAttribute(self.settings().WebAttribute.LocalContentCanAccessRemoteUrls,True) #Ustawianie mozliwosci komunikacji sieciowej dla widgetu
        self.channel = QWebChannel()

        page = self.page()
        page.setWebChannel(self.channel)
        self.channel.registerObject("backend",self.backend) # Przekazanie obiektu do JavaScriptu

        self.stationSelected = self.backend.stationSelected
        self.requestStationIndexValue = self.backend.requestStationIndexValue
        self.leaftletLoaded = self.backend.leaftletLoaded
        self.load(QUrl.fromLocalFile(map_path))

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