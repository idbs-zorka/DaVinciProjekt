from PySide6.QtWidgets import QWidget
from src.repository import Repository


class StationDetails(QWidget):

    def __init__(self,repository: Repository,station_id: int,parent: QWidget):
        super().__init__(parent=parent)
        self.station_id = station_id
        self.repository = repository

        self._build_layout()

    def _build_layout(self):
        
        pass


