from PySide6.QtWidgets import QApplication
from repository import Repository
from gui.station_select import StationSelectWidget

class Application(QApplication):
    station_select: StationSelectWidget

    def __init__(self,repository: Repository,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.repository = repository

    def run(self):
        self.station_select = StationSelectWidget(self.repository)
        self.station_select.show()
        self.exec()


