from datetime import datetime

import numpy as np
from PySide6.QtCharts import QChart, QChartView, QValueAxis, QDateTimeAxis, QSplineSeries
from PySide6.QtCore import QDateTime, Slot, QSize
from PySide6.QtGui import Qt, QPainter, QFont, QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QFormLayout, QComboBox, QDateTimeEdit, \
    QVBoxLayout, QPushButton, QMessageBox, QGroupBox, QGridLayout

from src.api.exceptions import APIError
from src.database.views import StationDetailsView
from src.gui.qt import qt_to_datetime
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
        self.setMinimumSize(QSize(700,500))
        self.repository = repository
        self.station_id = station_id
        self.sensors = self.repository.fetch_station_sensors(self.station_id)

        # Sensor select

        sensor_select = self._build_query_box()


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

        # Analytics data

        stats_box = self._build_stats_box()

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(sensor_select)
        self.layout.addWidget(self.chart_view, stretch=1)
        self.layout.addWidget(stats_box)

    def _build_query_box(self):
        box = QGroupBox("Wybierz sensor")

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
        box.setLayout(sensor_select_layout)
        return box


    def _build_stats_box(self):
        box = QGroupBox("Statystyki")
        font_val = QFont()
        font_val.setPointSize(10)
        font_val.setBold(True)

        grid = QHBoxLayout()
        # maks
        lbl_max = QLabel("Maksymalna:")
        val_max = QLabel("—")
        val_max.setFont(font_val)
        val_max.setStyleSheet("color: red;")
        grid.addWidget(lbl_max)
        grid.addWidget(val_max)

        # min
        lbl_min = QLabel("Minimalna:")
        val_min = QLabel("—")
        val_min.setFont(font_val)
        val_min.setStyleSheet("color: blue;")
        grid.addWidget(lbl_min)
        grid.addWidget(val_min)

        # trend
        lbl_trend = QLabel("Trend:")
        txt_trend = QLabel("—")
        txt_trend.setFont(font_val)
        grid.addWidget(lbl_trend)
        grid.addWidget(txt_trend)

        box.setLayout(grid)

        # przechowaj referencje, żeby potem się nie zgubiły
        self.stats = {
            "val_max": val_max,
            "val_min": val_min,
            "txt_trend": txt_trend
        }
        return box

    def load_data(self):
        current_sensor = self.sensor_combo.currentData()
        if not current_sensor:
            return

        # Pobranie zakresu czasowego
        dt_from = qt_to_datetime(self.date_from_edit.dateTime())
        dt_to = qt_to_datetime(self.date_to_edit.dateTime())

        # Fetch danych
        data = self.repository.fetch_sensor_data(
            current_sensor.id, dt_from, dt_to
        )

        if not data:
            QMessageBox.information(
                self, "Brak danych",
                "Brak dostępnych danych pomiarowych w wybranym zakresie!"
            )
            return

        # Zamiana na (timestamp_ms, value) i sortowanie
        numeric = sorted(
            ((int(entry.date.timestamp() * 1000), entry.value) for entry in data),
            key=lambda x: x[0]
        )
        xs, ys = zip(*numeric)

        # Ustawienie zakresów osi
        self.axis_x.setRange(
            QDateTime.fromMSecsSinceEpoch(xs[0]),
            QDateTime.fromMSecsSinceEpoch(xs[-1])
        )
        self.axis_y.setRange(0, max(ys) * 1.1)

        # Wypisanie serii
        self.series.clear()
        for x, y in numeric:
            self.series.append(x, y)

        # Obliczenie min/max
        min_idx = ys.index(min(ys))
        max_idx = ys.index(max(ys))
        min_ts, min_val = numeric[min_idx]
        max_ts, max_val = numeric[max_idx]
        min_dt = datetime.fromtimestamp(min_ts / 1000)
        max_dt = datetime.fromtimestamp(max_ts / 1000)

        self.stats['val_min'].setText(f"{min_val} ({min_dt})")
        self.stats['val_max'].setText(f"{max_val} ({max_dt})")
        # Obliczenie trendu (regresja liniowa)
        # weź czasy jako liczby (timestamp)
        x = np.array([sv.date.timestamp() for sv in data], dtype=float)
        y = np.array([sv.value for sv in data], dtype=float)

        # y = m * x + b
        A = np.vstack([x, np.ones_like(x)]).T
        m, _ = np.linalg.lstsq(A, y, rcond=None)[0]

        def trend_str():
            if m > 0:
                return "rosnący"
            elif m < 0:
                return "malejący"
            else:
                return "stały"

        self.stats['txt_trend'].setText(f"{trend_str()}")

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






