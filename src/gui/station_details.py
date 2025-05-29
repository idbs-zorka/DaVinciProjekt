from datetime import datetime

from PySide6.QtCharts import QChart, QLineSeries, QChartView, QValueAxis, QDateTimeAxis, QSplineSeries
from PySide6.QtCore import QDateTime, QMargins, QPoint, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QFormLayout, QComboBox, QDateTimeEdit, \
    QVBoxLayout, QPushButton

from src.database.views import StationDetailsView, SensorView
from src.repository import Repository
from src.gui.qt import datetime_to_qt,qt_to_datetime

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

        # top

        sensor_combo_label = QLabel("Sensor: ", self)
        sensor_combo = QComboBox(self,editable=True)
        sensor_combo.lineEdit().setReadOnly(True)
        sensor_combo.lineEdit().setPlaceholderText("Wybierz sensor")

        for sensor in self.sensors:
            sensor_combo.addItem(sensor.codename,userData=sensor)

        sensor_combo.setCurrentIndex(-1)

        now_dt = QDateTime.currentDateTime()
        from_dt = now_dt.addDays(-3)

        range_from_label = QLabel("Od: ", self)
        date_from_edit = QDateTimeEdit(self)
        date_from_edit.setDateTime(from_dt)
        date_from_edit.setMinimumDateTime(now_dt.addDays(-365))

        date_from_edit.setCalendarPopup(True)

        range_to_label = QLabel("Od: ", self)
        date_to_edit = QDateTimeEdit(self)
        date_to_edit.setCalendarPopup(True)

        display_btn = QPushButton("Wyświetl",self)
        display_btn.clicked.connect(self.on_display_btn)

        sensor_select_layout = QHBoxLayout()
        sensor_select_layout.addWidget(sensor_combo_label)
        sensor_select_layout.addWidget(sensor_combo)
        sensor_select_layout.addWidget(range_from_label)
        sensor_select_layout.addWidget(date_from_edit,stretch=1)
        sensor_select_layout.addWidget(range_to_label)
        sensor_select_layout.addWidget(date_to_edit,stretch=1)
        sensor_select_layout.addWidget(display_btn,stretch=1)


        # Chart

        self.chart = QChart()
        self.series = QSplineSeries()
        self.series.setName("Ayy")
        self.series.append(1,1)
        self.series.append(2,2)
        self.series.append(3,1)
        self.chart.addSeries(self.series)

        self.chart_view = QChartView(self.chart)

        self.layout = QVBoxLayout(self)
        self.layout.addLayout(sensor_select_layout)
        self.layout.addWidget(self.chart_view,stretch=1)

    @Slot(int)
    def on_display_btn(self):
        pass

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

        self.station_data_widget = StationDataWidget(
            repository=self.repository,
            station_id=self.station_id,
            parent=self
        )

        self.addTab(self.station_data_widget,"Dane")




