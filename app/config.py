import datetime
from datetime import timedelta,datetime
from typing import Literal
from enum import Enum

UPDATE_INTERVALS = {
    "station": timedelta(days=1),
    "aq_indexes": timedelta(hours=1)
}

AQ_INDEX_CATEGORIES = {
    -1: "Brak indeksu",
    0: "Bardzo dobry",
    1: "Dobry",
    2: "Umiarkowany",
    3: "Zły",
    4: "Bardzo zły",
    5: "Brak indeksu",
}

AQ_INDEX_CATEGORIES_COLORS = {
    -1: "#A9A9A9",  # Brak indeksu – ciemny szary
     0: "#009966",  # Bardzo dobry – ciemna zieleń
     1: "#66CC66",  # Dobry – jasna zieleń
     2: "#FFDE33",  # Umiarkowany – żółć
     3: "#FF9933",  # Zły – pomarańcz
     4: "#CC0033",  # Bardzo zły – czerwień
     5: "#A9A9A9",  # Brak indeksu – ciemny szary
}


AQ_TYPES = [
    "Ogólny",
    "SO2",
    "NO2",
    "PM10",
    "PM2.5",
    "O3"
]