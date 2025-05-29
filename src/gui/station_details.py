from datetime import datetime

from PySide6.QtCharts import QChart, QLineSeries, QChartView, QValueAxis, QDateTimeAxis, QSplineSeries
from PySide6.QtCore import QDateTime, QMargins, QPoint, Slot, QSize
from PySide6.QtGui import QColor, Qt, QPainter
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
        self.setMinimumSize(QSize(500,400))
        self.repository = repository
        self.station_id = station_id
        self.sensors = self.repository.fetch_station_sensors(self.station_id)

        # top

        sensor_combo_label = QLabel("Sensor: ", self)
        self.sensor_combo = QComboBox(self,editable=True)
        self.sensor_combo.lineEdit().setReadOnly(True)
        self.sensor_combo.lineEdit().setPlaceholderText("Wybierz sensor")

        for sensor in self.sensors:
            self.sensor_combo.addItem(sensor.codename,userData=sensor)

        self.sensor_combo.setCurrentIndex(-1)

        now_dt = QDateTime.currentDateTime()
        from_dt = now_dt.addDays(-3)

        range_from_label = QLabel("Od: ", self)
        self.date_from_edit = QDateTimeEdit(self)
        self.date_from_edit.setDateTime(from_dt)
        self.date_from_edit.setMinimumDateTime(now_dt.addDays(-365))
        self.date_from_edit.setCalendarPopup(True)

        range_to_label = QLabel("Od: ", self)
        self.date_to_edit = QDateTimeEdit(self)
        self.date_to_edit.setDateTime(now_dt)
        self.date_to_edit.setMaximumDateTime(now_dt)
        self.date_to_edit.setCalendarPopup(True)

        self.date_from_edit.setMaximumDateTime(self.date_to_edit.dateTime())
        self.date_to_edit.setMinimumDateTime(self.date_from_edit.dateTime())

        self.date_from_edit.dateTimeChanged.connect(lambda dt: self.date_to_edit.setMinimumDateTime(dt))
        self.date_to_edit.dateTimeChanged.connect(lambda dt: self.date_from_edit.setMaximumDateTime(dt))


        display_btn = QPushButton("Wyświetl",self)
        display_btn.clicked.connect(self.on_display_btn)

        sensor_select_layout = QHBoxLayout()
        sensor_select_layout.addWidget(sensor_combo_label)
        sensor_select_layout.addWidget(self.sensor_combo)
        sensor_select_layout.addWidget(range_from_label)
        sensor_select_layout.addWidget(self.date_from_edit,stretch=1)
        sensor_select_layout.addWidget(range_to_label)
        sensor_select_layout.addWidget(self.date_to_edit,stretch=1)
        sensor_select_layout.addWidget(display_btn,stretch=1)

        # Chart

        self.chart = QChart()

        self.series = QSplineSeries()

        self.chart.addSeries(self.series)
        self.chart.legend().setVisible(False)

        self.axis_x = QDateTimeAxis(format="MM-dd hh:mm")
        self.axis_x.setTitleText("Czas")
        self.axis_x.setTitleVisible(False)

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Wartość")
        self.axis_y.setTitleVisible(False)

        self.chart.addAxis(self.axis_x,Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y,Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing,True)

        self.layout = QVBoxLayout(self)
        self.layout.addLayout(sensor_select_layout)
        self.layout.addWidget(self.chart_view,stretch=1)

    def load_data(self):
        current_sensor: SensorView = self.sensor_combo.currentData()

        if current_sensor is None:
            return

        datetime_from = qt_to_datetime(self.date_from_edit.dateTime())
        datetime_to = qt_to_datetime(self.date_to_edit.dateTime())

        self.series.clear()

        data = [
            (int(entry.date.timestamp() * 1000), entry.value)
            for entry in self.repository.fetch_sensor_data(current_sensor.id, datetime_from, datetime_to)
        ]
        data.sort(key=lambda x: x[0])

        if data:
            xs,ys = zip(*data)

            self.axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(min(xs)),
                QDateTime.fromMSecsSinceEpoch(max(xs))
            )
            self.axis_y.setRange(
                0,max(ys) * 1.1
            )
        else:
            self.axis_x.setRange(self.date_from_edit.dateTime(),
                                 self.date_to_edit.dateTime())
            self.axis_y.setRange(0, 1)


        for ms,val in data:
            self.series.append(ms,val)

        min_x = min(data,key=lambda x:x[0])
        max_x = max(data,key=lambda x:x[0])

        


    @Slot()
    def on_display_btn(self):
        self.load_data()

class StationDetailsWidget(QTabWidget):

    def __init__(self,repository: Repository,station_id: int,parent: QWidget = None):
        super().__init__(parent=parent)
        self.station_id = station_id
        self.repository = repository
        self.details = repository.fetch_station_details_view(station_id)

        self._build_layout()

    def _build_layout(self):
        # all station data + sensors

        self.station_data_widget = StationDataWidget(
            repository=self.repository,
            station_id=self.station_id,
            parent=self
        )

        self.addTab(self.station_data_widget,"Dane")

        details = self.repository.fetch_station_details_view(self.station_id)
        self.station_info_widget = StationInfoWidget(details, parent=self)
        self.addTab(self.station_info_widget,"Informacje")






