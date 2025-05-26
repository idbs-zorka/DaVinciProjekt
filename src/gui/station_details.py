from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QTableWidget, QFormLayout, QScrollArea
from src.repository import Repository
from src.database.views import StationDetailsView
from PySide6.QtCharts import QChart
class StationInfoWidget(QWidget):
    def __init__(self,station_details: StationDetailsView,parent : QWidget = None):
        super().__init__(parent=parent)
        self.station_details = station_details

        details = {
            "Kod stacji": station_details.codename,
            "Nazwa": station_details.name,
            "Powiat": station_details.district,
            "Województwo": station_details.voivodeship,
            "Miasto": station_details.city,
            "Adres": station_details.address
        }

        form = QFormLayout(self)

        for key,val in details.items():
            form.addRow(key,QLabel(val))

        self.setLayout(form)


class StationDataWidget(QWidget):
    def __init__(self,repository: Repository,station_id: int,parent: QWidget = None):
        super().__init__(parent=parent)
        self.repository = repository
        self.station_id = station_id
        self.sensors = self.repository.fetch_station_sensors(self.station_id)
        layout = QHBoxLayout(self)
        label = QLabel("Hello",self)
        layout.addWidget(label)


class StationDetailsWidget(QTabWidget):

    def __init__(self,repository: Repository,station_id: int,parent: QWidget = None):
        super().__init__(parent=parent)
        self.station_id = station_id
        self.repository = repository
        self.details = repository.fetch_station_details_view(station_id)

        self._build_layout()

    def _build_layout(self):
        # all station data + sensors

        details = self.repository.fetch_station_details_view(self.station_id)
        self.station_info_widget = StationInfoWidget(details, parent=self)
        self.addTab(self.station_info_widget,"Informacje")

        self.station_data_widget = StationDataWidget(self.repository,self.station_id,self)
        self.addTab(self.station_data_widget,"Dane")




