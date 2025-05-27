from datetime import datetime

from PySide6.QtCharts import QChart, QLineSeries, QChartView, QValueAxis, QDateTimeAxis
from PySide6.QtCore import QDateTime, QMargins
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QFormLayout, QComboBox, QDateTimeEdit

from src.database.views import StationDetailsView, SensorView
from src.repository import Repository


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

        # Left

        # Sensor selection
        self.sensor_combo = QComboBox(self,editable=True)
        self.sensor_combo.lineEdit().setReadOnly(True)
        self.sensor_combo.lineEdit().setPlaceholderText("Wybierz sensor")
        for sensor in [*self.sensors]:
            self.sensor_combo.addItem(sensor.codename,userData=sensor)

        self.sensor_combo.setCurrentIndex(-1)

        self.sensor_combo.currentIndexChanged.connect(lambda x: self.on_sensor_changed(self.sensor_combo.itemData(x)))

        # Date range selection

        current_datetime = QDateTime.currentDateTime()
        last_datetime = current_datetime.addDays(-365)

        self.date_from_edit = QDateTimeEdit(self)
        self.date_from_edit.setDateTime(current_datetime.addDays(-3))
        self.date_from_edit.setMinimumDateTime(last_datetime)

        self.date_to_edit = QDateTimeEdit(self)
        self.date_to_edit.setDateTime(QDateTime.currentDateTime())
        self.date_to_edit.setMaximumDateTime(QDateTime.currentDateTime())

        filter_layout = QFormLayout()
        filter_layout.addRow("Typ sensora",self.sensor_combo)
        filter_layout.addRow("Od", self.date_from_edit)
        filter_layout.addRow("Do", self.date_to_edit)

        # right

        self.chart_widget = QChartView(self)
        self.chart = QChart()
        self.chart.setBackgroundBrush(QColor.fromRgba(0x00000000))
        self.chart.setMargins(QMargins(0,0,0,0))
        self.chart_widget.setChart(self.chart)

        self.layout = QHBoxLayout(self)
        self.layout.addLayout(filter_layout)
        self.layout.addWidget(self.chart_widget)

    def load_chart_data(self):
        # Jeśli nie wybrano czujnika, nic nie rób
        if self.sensor_combo.currentIndex() == -1:
            return

        # Pobierz wybrany sensor i zakres czasowy (w milisekundach od epoki)
        sensor: SensorView = self.sensor_combo.currentData()
        date_from_ms = self.date_from_edit.dateTime().toMSecsSinceEpoch()
        date_to_ms = self.date_to_edit.dateTime().toMSecsSinceEpoch()

        # Fetch danych z repozytorium (zakładam, że entry.date to datetime)
        data = self.repository.fetch_sensor_data(
            sensor.id,
            datetime.fromtimestamp(date_from_ms / 1000.0),
            datetime.fromtimestamp(date_to_ms / 1000.0)
        )

        # Czyścimy wykres i poprzednie serie
        self.chart.removeAllSeries()

        # Tworzymy nową serię i wypełniamy punktami
        series = QLineSeries()
        for entry in data:
            # Konwertujemy datetime na milisekundy od epoki, zgodnie z QDateTimeAxis
            ms = int(entry.date.timestamp() * 1000)
            series.append(ms, entry.value)

        # Dodajemy serię do wykresu
        self.chart.addSeries(series)

        # Ustawiamy oś czasu (X) i oś wartości (Y)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd HH:mm")
        axis_x.setTitleText("Czas")
        axis_x.setTickCount(6)
        axis_x.setMin(QDateTime.fromMSecsSinceEpoch(date_from_ms))
        axis_x.setMax(QDateTime.fromMSecsSinceEpoch(date_to_ms))

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.2f")
        axis_y.setTitleText("Wartość")
        # Automatyczne dopasowanie zakresu Y do danych
        values = [entry.value for entry in data]
        if values:
            axis_y.setMin(min(values))
            axis_y.setMax(max(values))

        # Przypisujemy osie do serii
        self.chart.setAxisX(axis_x, series)
        self.chart.setAxisY(axis_y, series)

    def on_sensor_changed(self,sensor: SensorView):
        self.load_chart_data()


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




