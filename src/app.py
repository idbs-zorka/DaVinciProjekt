from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication, QDialog, QBoxLayout, QVBoxLayout  # Biblioteka graficzna
from repository import Repository
from gui.station_select import StationSelectWidget
from gui.station_details import StationDetailsWidget

class Application(QApplication):
    station_select: StationSelectWidget
    station_details: StationDetailsWidget

    def __init__(self,repository: Repository,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.repository = repository

    def run(self):
        self.station_select = StationSelectWidget(self.repository)
        self.station_select.stationSelected.connect(self.open_station_details)

        self.station_select.show()
        self.exec()

    @Slot(int)
    def open_station_details(self,station_id: int):
        dialog = QDialog(self.station_select)
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        self.station_details = StationDetailsWidget(self.repository, station_id, dialog)
        layout.addWidget(self.station_details)
        dialog.show()
