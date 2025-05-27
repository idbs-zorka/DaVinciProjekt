from datetime import datetime

from PySide6.QtCore import Qt, Slot, QDateTime, QMargins
from PySide6.QtGui import QColor, QColorConstants
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTabWidget, QTableWidget, QFormLayout, QScrollArea, \
    QCheckBox, QComboBox, QDateTimeEdit

from src.api.models import Sensor
from src.repository import Repository
from src.database.views import StationDetailsView, SensorView
from PySide6.QtCharts import QChart, QLineSeries, QLegend, QChartView, QValueAxis, QDateTimeAxis


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


from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateTimeEdit, QToolTip
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis


class StationDataWidget(QWidget):
    """
    A QWidget that displays time-series data for a selected sensor and date range.
    This refactored version improves clarity, applies a dark theme to the chart,
    automatically updates when inputs change, and adds tooltips and a legend.
    """

    def __init__(self, repository:Repository,station_id:int, parent=None):
        super().__init__(parent)
        # Initialize UI components and chart
        self.repository = repository
        self.station_id = station_id

        self._init_ui()
        self._init_chart()
        self._init_signals()
        # Initial chart update
        self.update_chart()

    def _init_ui(self):
        """Set up sensor selection and date range input controls."""
        # Layout for controls
        control_layout = QHBoxLayout()

        # Sensor selection combo box
        sensor_label = QLabel("Sensor:")

        # Sensor combo
        self.sensor_combo = QComboBox(editable=True)
        self.sensor_combo.lineEdit().setReadOnly(True)
        self.sensor_combo.lineEdit().setPlaceholderText("Wybierz sensor")
        self.sensor_combo.setCurrentIndex(-1)

        # Example sensor list; replace with real sensor names
        self.sensors_list = self.repository.fetch_station_sensors(self.station_id)

        for sensor in self.sensors_list:
            self.sensor_combo.addItem(sensor.codename,userData=sensor)

        # Start date/time input
        start_label = QLabel("Start:")
        self.start_datetime = QDateTimeEdit(QDateTime.currentDateTime().addDays(-7))
        self.start_datetime.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.start_datetime.setCalendarPopup(True)

        # End date/time input
        end_label = QLabel("End:")
        self.end_datetime = QDateTimeEdit(QDateTime.currentDateTime())
        self.end_datetime.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.end_datetime.setCalendarPopup(True)

        # Add widgets to control layout
        control_layout.addWidget(sensor_label)
        control_layout.addWidget(self.sensor_combo)
        control_layout.addStretch(1)
        control_layout.addWidget(start_label)
        control_layout.addWidget(self.start_datetime)
        control_layout.addWidget(end_label)
        control_layout.addWidget(self.end_datetime)

        # Main vertical layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addLayout(control_layout)

    def _init_chart(self):
        """Set up the QChart, axes, series, and view with dark theme styling."""
        # Create chart and apply dark theme
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartTheme.ChartThemeDark)  # Use built-in dark theme:contentReference[oaicite:6]{index=6}
        # Manually set background color (dark gray)
        self.chart.setBackgroundBrush(
            QBrush(QColor("#121212")))  # Dark background for contrast:contentReference[oaicite:7]{index=7}
        self.chart.setBackgroundRoundness(0)  # No rounded corners

        # Create axes
        self.axis_x = QDateTimeAxis()
        self.axis_x.setFormat("yyyy-MM-dd hh:mm")  # Display format for dates:contentReference[oaicite:8]{index=8}
        self.axis_x.setLabelsColor(Qt.GlobalColor.white)
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setGridLineColor(QColor(80, 80, 80))

        self.axis_y = QValueAxis()
        self.axis_y.setLabelFormat("%.2f")
        self.axis_y.setLabelsColor(Qt.GlobalColor.white)
        self.axis_y.setGridLineVisible(True)
        self.axis_y.setGridLineColor(QColor(80, 80, 80))
        self.axis_y.setTitleText("Value")
        self.axis_y.setTitleBrush(QBrush(Qt.GlobalColor.white))

        # Add axes to chart
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)

        # Create line series
        self.series = QLineSeries()
        # Name the series for the legend
        self.series.setName("Sensor Data")
        # Use anti-aliased pen for clarity
        series_pen = QPen(QColor("#00BCD4"))  # Use a distinct color (teal) for the line
        series_pen.setWidth(2)
        self.series.setPen(series_pen)
        # Enable OpenGL acceleration for performance on moderate datasets:contentReference[oaicite:9]{index=9}
        self.series.setUseOpenGL(True)
        # Allow hover events on points
        self.series.setPointsVisible(True)

        # Add series to chart and attach to axes
        self.chart.addSeries(self.series)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)

        # Show legend with series name
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)  # Legend at bottom:contentReference[oaicite:10]{index=10}
        # Set legend text color to white (for dark theme readability)
        self.chart.legend().setLabelColor(Qt.GlobalColor.white)

        # Create chart view with antialiasing for smoother rendering
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Disable drop shadow for cleaner dark appearance (improves performance)
        self.chart.setDropShadowEnabled(False)

        # Add chart view to the main layout
        self.main_layout.addWidget(self.chart_view)

    def _init_signals(self):
        """Connect signals for interactive behavior."""
        # Update chart when sensor selection or date range changes
        self.sensor_combo.currentTextChanged.connect(self.update_chart)
        self.start_datetime.dateTimeChanged.connect(self.update_chart)
        self.end_datetime.dateTimeChanged.connect(self.update_chart)
        # Show tooltip on data point hover
        self.series.hovered.connect(self.show_point_tooltip)  # Hover signal:contentReference[oaicite:11]{index=11}

    def show_point_tooltip(self, point, state):
        """Display a tooltip when hovering over a data point."""
        if state:  # Mouse entered point
            # Convert x (ms since epoch) back to QDateTime
            timestamp = QDateTime.fromMSecsSinceEpoch(int(point.x()))
            # Format tooltip text
            text = f"{timestamp.toString('yyyy-MM-dd hh:mm:ss')}\nValue: {point.y():.2f}"
            # Show tooltip at cursor position
            QToolTip.showText(QCursor.pos(), text)
        else:
            # Hide tooltip when not hovering
            QToolTip.hideText()

    def fetch_data(self, sensor_name, start_msec, end_msec):
        """
        Fetch sensor data between start and end timestamps (in milliseconds).
        This is a placeholder function: replace with actual data access logic.
        Returns a list of (timestamp_msec, value) tuples.
        """
        # Example dummy data: a simple line
        data = []
        if sensor_name:
            dt = start_msec
            step = (end_msec - start_msec) / 100 if end_msec > start_msec else 1
            value = 0.0
            while dt <= end_msec:
                data.append((dt, value))
                dt += step
                value += 1.0  # just an example trend
        return data

    def update_chart(self):
        """Re-generate the chart data for the selected sensor and date range."""
        sensor = self.sensor_combo.currentText()
        start_dt = self.start_datetime.dateTime()
        end_dt = self.end_datetime.dateTime()

        # Ensure valid date range
        if start_dt > end_dt:
            # Swap if out-of-order
            start_dt, end_dt = end_dt, start_dt

        # Convert to milliseconds since epoch for consistency
        start_msec = start_dt.toMSecsSinceEpoch()
        end_msec = end_dt.toMSecsSinceEpoch()

        # Retrieve data points for the sensor and date range
        data = self.fetch_data(sensor, start_msec, end_msec)

        # Clear any existing data
        self.series.clear()

        # Populate series with new data points
        for timestamp, value in data:
            self.series.append(timestamp, value)

        # Update axis ranges based on data
        if data:
            # Y-axis range from min to max data value
            values = [v for (_, v) in data]
            min_val, max_val = min(values), max(values)
            self.axis_y.setRange(min_val, max_val)
        else:
            # Default range if no data
            self.axis_y.setRange(0, 1)

        # X-axis range from start to end date/time
        self.axis_x.setRange(start_dt, end_dt)


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

        self.station_data_widget = StationDataWidget(parent=self)
        self.addTab(self.station_data_widget,"Dane")




