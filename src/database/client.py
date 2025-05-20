import typing
from datetime import datetime
import sqlite3
from enum import Enum

import src.api.client as api
import src.database.views as views
from src.api.models import IndexCategory
import src.config as config


class Client:
    """
    Klient bazy danych SQLite odpowiedzialny za:
      - inicjalizację i migrację schematu,
      - przechowywanie i aktualizację danych o stacjach oraz wskaźnikach jakości powietrza,
      - odczyt widoków z tabel.
    """

    OVERALL_SENSOR_TYPE_CODENAME: str = "Ogólny"

    class GlobalUpdateIds(Enum):
        """
        Identyfikatory rekordów w tabeli `global_update` służące
        do śledzenia momentów ostatniej globalnej aktualizacji.
        """
        STATION_LIST = 0

    def __init__(self, file: str):
        """
        Inicjalizuje połączenie z bazą danych i tworzy niezbędne tabele.

        Args:
            file (str): Ścieżka do pliku SQLite.
        """
        self.__conn = sqlite3.connect(file)
        self.__conn.row_factory = sqlite3.Row
        self.__cursor = self.__conn.cursor()
        self.__populate_tables()

    def __populate_tables(self):
        """
        Tworzy w bazie wszystkie potrzebne tabele i triggery,
        jeżeli jeszcze nie istnieją, oraz inicjalizuje podstawowe wartości.
        """
        # Tabela globalnych znaczników aktualizacji
        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_update (
                id INTEGER PRIMARY KEY,
                last_update_at TIMESTAMP NOT NULL DEFAULT 0
            )
        """)

        # Wstawienie brakujących identyfikatorów
        self.__cursor.executemany("""
            INSERT OR IGNORE INTO global_update (id)
                VALUES (?)
        """, [(member.value,) for member in self.GlobalUpdateIds])

        # Tabele stacji i powiązane
        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS city (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                voivodeship TEXT NOT NULL,
                city TEXT NOT NULL UNIQUE
            )
        """)

        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS station_update (
                station_id INTEGER UNIQUE,
                last_sensors_update_at TIMESTAMP NOT NULL DEFAULT 0,
                last_indexes_update_at TIMESTAMP NOT NULL DEFAULT 0,
                last_meta_update_at TIMESTAMP NOT NULL DEFAULT 0,
                FOREIGN KEY (station_id) REFERENCES station(id) ON UPDATE CASCADE
            )
        """)

        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS station (
                id INTEGER PRIMARY KEY,
                codename TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                city_id INTEGER,
                address TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                FOREIGN KEY (city_id) REFERENCES city(id)
            )
        """)

        # Triggery aktualizujące global_update przy zmianach w station
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_insert_station
            AFTER INSERT ON station
            BEGIN
                UPDATE global_update
                SET last_update_at = unixepoch('now')
                WHERE id = {self.GlobalUpdateIds.STATION_LIST.value};
            END
        """)
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_update_station
            AFTER UPDATE ON station
            BEGIN
                UPDATE global_update
                SET last_update_at = unixepoch('now')
                WHERE id = {self.GlobalUpdateIds.STATION_LIST.value};
            END
        """)

        # Tabela metadanych stacji i triggery do ich śledzenia
        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS station_meta (
                station_id INTEGER NOT NULL,
                international_codename TEXT NOT NULL,
                launch_date DATE,
                shutdown_date DATE,
                type TEXT,
                FOREIGN KEY (station_id) REFERENCES station(id) ON UPDATE CASCADE
            )
        """)
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_insert_station_meta
            AFTER INSERT ON station_meta
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO station_update
                (station_id, last_meta_update_at)
                VALUES (NEW.station_id, unixepoch('now'));
            END
        """)
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_update_station_meta
            AFTER UPDATE ON station_meta
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO station_update
                (station_id, last_meta_update_at)
                VALUES (NEW.station_id, unixepoch('now'));
            END
        """)

        # Kategorie indeksów i nazwy sensorów
        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS aq_index_category_name (
                value INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        # Wypełnienie domyślnych nazwy kategorii indeksów
        self.__cursor.executemany("""
            INSERT OR IGNORE INTO aq_index_category_name (value, name)
            VALUES (?, ?)
        """, ((idx, val) for idx, val in config.AQ_INDEX_CATEGORIES.items()))

        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_type (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codename TEXT NOT NULL UNIQUE
            )
        """)
        # Wypełnienie domyślnych typów sensorów
        self.__cursor.executemany("""
            INSERT OR IGNORE INTO sensor_type (codename)
            VALUES (?)
        """, ((t,) for t in config.AQ_TYPES))


        # Tabela przechowująca indeksy jakości powietrza i triggery
        self.__cursor.execute("""
            CREATE TABLE IF NOT EXISTS aq_index (
                station_id INT,
                sensor_type_id INT,
                value INT,
                record_date DATETIME,
                FOREIGN KEY (station_id) REFERENCES station(id) ON UPDATE CASCADE,
                FOREIGN KEY (sensor_type_id) REFERENCES sensor_type(id),
                FOREIGN KEY (value) REFERENCES aq_index_category_name(value)
            )
        """)
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_insert_aq_index
            AFTER INSERT ON aq_index
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO station_update
                (station_id, last_indexes_update_at)
                VALUES (NEW.station_id, unixepoch('now'));
            END
        """)
        self.__cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS tgr_on_update_aq_index
            AFTER UPDATE ON aq_index
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO station_update
                (station_id, last_indexes_update_at)
                VALUES (NEW.station_id, unixepoch('now'));
            END
        """)
        self.__conn.commit()

    def update_stations(self, stations: typing.Iterable[api.models.Station]):
        """
        Zapisuje lub uaktualnia listę stacji wraz z informacjami o mieście.

        Args:
            stations (Iterable[api.models.Station]): Kolekcja obiektów Station
                pobranych z API.
        """

        # Wstawianie/ignorowanie miast
        city_params = (
            (s.district, s.voivodeship, s.city)
            for s in stations
        )
        self.__cursor.executemany("""
            INSERT OR IGNORE INTO city (district, voivodeship, city)
            VALUES (?, ?, ?)
        """, city_params)

        # Wstawianie/aktualizacja stacji
        station_params = [
            {
                "id": s.id,
                "codename": s.codename,
                "name": s.name,
                "address": s.address,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "city": s.city
            } for s in stations
        ]
        self.__cursor.executemany("""
            INSERT OR REPLACE INTO station
            (id, codename, name, city_id, address, latitude, longitude)
            SELECT
              :id, :codename, :name, city.id, :address, :latitude, :longitude
            FROM city WHERE city.city = :city
        """, station_params)
        self.__conn.commit()

    def get_last_stations_update(self) -> datetime:
        """
        Pobiera czas ostatniej globalnej aktualizacji listy stacji.

        Returns:
            datetime: Data i godzina ostatniej aktualizacji.
        """
        qry = self.__cursor.execute(
            "SELECT last_update_at FROM global_update WHERE id = ?",
            [self.GlobalUpdateIds.STATION_LIST.value]
        ).fetchone()
        return datetime.fromtimestamp(qry["last_update_at"])

    def get_station_list_view(self) -> list[views.StationListView]:
        """
        Zwraca zrekonstruowany widok listy stacji.

        Returns:
            list[views.StationListView]: Lista widoków stacji z podstawowymi danymi.
        """
        qry = self.__cursor.execute("""
            SELECT s.id, s.name, s.latitude, s.longitude, c.city
            FROM station AS s
            JOIN city AS c ON c.id = s.city_id
        """)
        return [
            views.StationListView(
                id=row["id"],
                name=row["name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                city=row["city"]
            ) for row in qry
        ]

    def update_station_meta(self, meta: list[api.models.StationMeta]):
        """
        Zapisuje lub uaktualnia metadane stacji (międzynarodowy kod, daty, typ).

        Args:
            meta (list[api.models.StationMeta]): Lista obiektów meta pobranych z API.
        """
        params = (
            {
                "codename": m.codename,
                "international": m.international_codename,
                "launch_date": m.launch_date.isoformat(),
                "shutdown_date": m.close_date.isoformat(),
                "type": m.type
            } for m in meta
        )
        self.__cursor.executemany("""
            INSERT OR REPLACE INTO station_meta
            (station_id, international_codename, launch_date, shutdown_date, type)
            VALUES (?, ?, ?, ?, ?)
        """, params)
        self.__conn.commit()

    def fetch_last_station_meta_update(self, station_id: int) -> datetime:
        """
        Pobiera czas ostatniej aktualizacji metadanych danej stacji.

        Args:
            station_id (int): Identyfikator stacji.

        Returns:
            datetime: Data i godzina ostatniej aktualizacji metadanych.
        """
        qry = self.__cursor.execute("""
            SELECT last_meta_update_at
            FROM station_update
            WHERE station_id = ?
        """, (station_id,)).fetchone()
        return datetime.fromtimestamp(qry["last_meta_update_at"])

    def fetch_station_detail_view(self) -> views.StationDetailsView:
        """
        Zwraca widok szczegółów stacji.

        Returns:
            views.StationDetailsView: Szczegółowy widok jednej stacji.

        Raises:
            NotImplementedError: Metoda jeszcze nie zaimplementowana.
        """
        raise NotImplementedError("Metoda `fetch_station_detail_view` nie została jeszcze zaimplementowana.")

    def update_sensor_types(self, types: list[str]):
        """
        Dodaje nowe typy sensorów do słownika `sensor_type`.

        Args:
            types (list[str]): Lista kodowych nazw typów sensorów.
        """
        params = ((t,) for t in types)
        self.__cursor.executemany(
            "INSERT OR IGNORE INTO sensor_type (codename) VALUES (?)",
            params
        )
        self.__conn.commit()

    def update_station_air_quality_indexes(
        self,
        station_id: int,
        indexes: api.models.AirQualityIndexes
    ):
        """
        Zapisuje lub uaktualnia wartości indeksów jakości powietrza dla stacji.

        Args:
            station_id (int): Identyfikator stacji.
            indexes (api.models.AirQualityIndexes): Obiekt zawierający
                ogólny indeks oraz indeksy poszczególnych sensorów.
        """
        all_indexes = (
            (self.OVERALL_SENSOR_TYPE_CODENAME, indexes.overall),
            *indexes.sensors.items()
        )
        params = (
            {
                "station_id": station_id,
                "value": idx.value,
                "sensor_codename": key,
                "date": idx.date.isoformat() if (idx.date is not None) else None
            }
            for key, idx in all_indexes
        )
        self.__cursor.executemany("""
            INSERT OR REPLACE INTO aq_index
            (station_id, sensor_type_id, value, record_date)
            SELECT
              :station_id,
              st.id,
              :value,
              :date
            FROM sensor_type AS st
            WHERE st.codename = :sensor_codename
        """, params)
        self.__conn.commit()

    def fetch_last_station_air_quality_indexes_update(self, station_id: int) -> datetime:
        """
        Pobiera czas ostatniej aktualizacji indeksów jakości powietrza dla stacji.

        Args:
            station_id (int): Identyfikator stacji.

        Returns:
            datetime: Data i godzina ostatniej aktualizacji indeksów,
                lub epoch (1970-01-01) jeśli brak wpisu.
        """
        qry = self.__cursor.execute("""
            SELECT last_indexes_update_at
            FROM station_update
            WHERE station_id = ?
        """, (station_id,)).fetchone()
        if qry is not None:
            return datetime.fromtimestamp(qry["last_indexes_update_at"])

        return datetime.fromtimestamp(0)

    def fetch_station_air_quality_indexes(self, station_id: int) -> list[views.AQIndexView]:
        """
        Zwraca widoki indeksów jakości powietrza dla podanej stacji.

        Args:
            station_id (int): Identyfikator stacji.

        Returns:
            list[views.AQIndexView]: Lista widoków z nazwą sensora, wartością i kategorią.
        """
        qry = self.__cursor.execute("""
            SELECT
                st.codename AS codename,
                aq.value AS value,
                cat.name AS category
            FROM aq_index AS aq
            JOIN sensor_type AS st ON st.id = aq.sensor_type_id
            JOIN aq_index_category_name AS cat ON cat.value = aq.value
            WHERE aq.station_id = ?
        """, (station_id,)).fetchall()
        return [
            views.AQIndexView(
                codename=row["codename"],
                value=row["value"],
                category=row["category"]
            ) for row in qry
        ]
