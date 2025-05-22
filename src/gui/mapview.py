from PySide6.QtCore import Qt, QObject, Slot, QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtQuickWidgets import QQuickWidget
from pathlib import Path

class MapViewBackend(QObject):

    #               latitude, longitude, name, color
    addMarker = Signal(float,float,str,str)
    resetMarkers = Signal()
    setPosition = Signal(float,float)

    markerClicked = Signal(str)
    @Slot(str)
    def on_marker_click(self,name: str):
        print(f"Clicked: {name}")
        self.markerClicked.emit(name)

class MapViewWidget(QWebEngineView):
    markerClicked = Signal(str)
    backend = MapViewBackend()

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        map_path = Path(__file__).with_name("mapview.html").resolve()

        self.settings().setAttribute(self.settings().WebAttribute.LocalContentCanAccessRemoteUrls,True)
        self.load(QUrl.fromLocalFile(map_path))
        self.channel = QWebChannel()
        self.channel.registerObject("backend",self.backend)
        self.page().setWebChannel(self.channel)

    def add_marker(self,lat,lng,name,color):
        self.backend.addMarker.emit(lat,lng,name,color)

    def reset_markers(self):
        self.backend.resetMarkers.emit()

    def set_position(self,lat: float,lng: float):
        self.backend.setPosition.emit(lat,lng)
