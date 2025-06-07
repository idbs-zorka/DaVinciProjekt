from datetime import datetime

import numpy as np
from PySide6.QtCharts import QChart, QChartView, QValueAxis, QDateTimeAxis, QSplineSeries, QScatterSeries
from PySide6.QtCore import QDateTime, Slot, QSize, QPointF
from PySide6.QtGui import Qt, QPainter, QFont, QPixmap, QColorConstants, QCursor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QFormLayout, QComboBox, QDateTimeEdit, \
    QVBoxLayout, QPushButton, QMessageBox, QGroupBox, QGridLayout, QToolTip

from src.api.exceptions import APIError
from src.database.views import StationDetailsView, SensorView
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

        # ---------------------------------------------------------
        # 1. Utworzenie wykresu i osi
        # ---------------------------------------------------------
        self.chart = QChart()
        self.chart.legend().setVisible(False)

        self.axis_x = QDateTimeAxis(format="MM-dd hh:mm")
        self.axis_x.setTitleText("Czas")
        self.axis_x.setTitleVisible(False)

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Wartość")
        self.axis_y.setTitleVisible(False)

        # Dodajemy osie do wykresu ZANIM będziemy do nich przyczepiać serie
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)

        # ---------------------------------------------------------
        # 2. Główna seria (QSplineSeries)
        # ---------------------------------------------------------
        self.series = QSplineSeries()
        self.series.hovered.connect(self._on_point_hovered)
        # 2.1 Dodajemy serię do wykresu
        self.chart.addSeries(self.series)

        # 2.2 Teraz przyczepiamy już dodaną serię do istniejących osi
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)

        # ---------------------------------------------------------
        # 3. Seria punktów minimalnych (QScatterSeries)
        # ---------------------------------------------------------
        self.min_scatter = QScatterSeries()
        self.min_scatter.setName("Minimum")
        self.min_scatter.setMarkerSize(12)
        self.min_scatter.setColor(QColorConstants.Blue)

        # 3.1 Dodajemy serię punktów do wykresu
        self.chart.addSeries(self.min_scatter)

        # 3.2 Przyczepiamy ją do tej samej osi X i Y co główną serię
        self.min_scatter.attachAxis(self.axis_x)
        self.min_scatter.attachAxis(self.axis_y)

        # ---------------------------------------------------------
        # 4. Seria punktów maksymalnych (QScatterSeries)
        # ---------------------------------------------------------
        self.max_scatter = QScatterSeries()
        self.max_scatter.setName("Maksimum")
        self.max_scatter.setMarkerSize(12)
        self.max_scatter.setColor(QColorConstants.Red)

        # 4.1 Dodajemy serię punktów do wykresu
        self.chart.addSeries(self.max_scatter)

        # 4.2 Przyczepiamy ją do tej samej osi X i Y co reszta wykresu
        self.max_scatter.attachAxis(self.axis_x)
        self.max_scatter.attachAxis(self.axis_y)

        # ---------------------------------------------------------
        # 5. QChartView
        # ---------------------------------------------------------
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)

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

        grid = QGridLayout()

        # maks
        max_layout = QHBoxLayout()
        max_label = QLabel("Maksymalna:")
        self.max_value_label = QLabel("—")
        self.max_value_label.setFont(font_val)
        self.max_value_label.setStyleSheet("color: red;")
        max_layout.addWidget(max_label)
        max_layout.addWidget(self.max_value_label)

        # min
        min_layout = QHBoxLayout()
        min_label = QLabel("Minimalna:")
        self.min_value_label = QLabel("—")
        self.min_value_label.setFont(font_val)
        self.min_value_label.setStyleSheet("color: blue;")
        min_layout.addWidget(min_label)
        min_layout.addWidget(self.min_value_label)

        # avg

        avg_layout = QHBoxLayout()
        avg_label = QLabel("Średnia:")
        self.avg_value_label = QLabel("—")
        self.avg_value_label.setFont(font_val)
        self.avg_value_label.setStyleSheet("color: white;")
        avg_layout.addWidget(avg_label)
        avg_layout.addWidget(self.avg_value_label)

        # trend
        trend_layout = QHBoxLayout()
        trend_label = QLabel("Trend:")
        self.trend_value_label = QLabel("—")
        self.trend_value_label.setFont(font_val)
        self.trend_value_label.setStyleSheet("color: white;")
        trend_layout.addWidget(trend_label)
        trend_layout.addWidget(self.trend_value_label)

        grid = QGridLayout()
        grid.addLayout(max_layout, 0, 0)
        grid.addLayout(min_layout, 0, 1)
        grid.addLayout(avg_layout, 1, 0)
        grid.addLayout(trend_layout, 1, 1)
        box.setLayout(grid)
        return box

    def load_data(self):
        current_sensor: SensorView = self.sensor_combo.currentData()
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
        self.min_scatter.clear()
        self.max_scatter.clear()

        for x, y in numeric:
            self.series.append(x, y)

        # Obliczenie min/max
        min_idx = ys.index(min(ys))
        max_idx = ys.index(max(ys))
        min_ts, min_val = numeric[min_idx]
        max_ts, max_val = numeric[max_idx]
        min_dt = datetime.fromtimestamp(min_ts / 1000)
        max_dt = datetime.fromtimestamp(max_ts / 1000)

        avg_val = np.average(ys)

        self.min_value_label.setText(f"{min_val:.2f} µg/m³ ({min_dt})")
        self.max_value_label.setText(f"{max_val:.2f} µg/m³ ({max_dt})")
        self.avg_value_label.setText(f"{avg_val:.4f} µg/m³")

        self.min_scatter.append(min_ts,min_val)
        self.max_scatter.append(max_ts,max_val)

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

        self.trend_value_label.setText(f"{trend_str()}")

    @Slot()
    def on_display_btn(self):
        date_from = self.date_from_edit.dateTime()
        date_to = self.date_to_edit.dateTime()
        days_diff = date_from.daysTo(date_to)

        if days_diff > 30:
            QMessageBox.warning(
                self,
                "Błędny zakres",
                "Możesz wyświetlić maksymalnie 30 dni naraz, popraw zakres"
            )
            return

        self.load_data()

    @Slot(QPointF,bool)
    def _on_point_hovered(self, point: QPointF, state: bool):
        """
        point.x() – to timestamp w milisekundach (QPointF.x zwraca double),
        point.y() – to wartość pomiaru (double).
        state == True  => kursor właśnie wszedł na ten punkt,
        state == False => kursor wyszedł z punktu (można zamknąć tooltip, jeśli chcemy).
        """
        if not state:
            # Możemy opcjonalnie ukryć tooltip; w Qt tooltip wygaśnie samodzielnie, więc nie musimy tu nic robić.
            return

        # 1. Konwersja x (double = ms od epoch) na QDateTime
        ts_ms = int(point.x())
        dt = QDateTime.fromMSecsSinceEpoch(ts_ms, Qt.TimeSpec.LocalTime)

        # 2. Formatowanie daty w preferowany sposób, np. "YYYY-MM-dd hh:mm"
        data_str = dt.toString("yyyy-MM-dd hh:mm")

        # 3. Wartość pomiaru
        wartosc = point.y()

        # 4. Przygotowanie tekstu pod tooltip
        text = f"{data_str}\n{wartosc:.2f} µg/m³"

        # 5. Wyświetlamy tooltip pod kursorem
        QToolTip.setFont(QFont("SansSerif", 10))  # ustal font, jeśli chcesz
        QToolTip.showText(
            QCursor.pos(),
            text,
            self.chart_view,
            self.chart_view.rect(),
            3000     # <-- wyświetl przez 3000 ms
        )
        # Jeśli chcesz, żeby tooltip znikał, gdy kursor opuści punkt, nie musisz nic robić
        # – Qt sam schowa go po chwili lub gdy kursor się przesunie.

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






