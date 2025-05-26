from src.api.client import Client as APIClient
from src.database.client import Client as DatabaseClient
import src.database.views as views

from datetime import datetime

from src.config import UPDATE_INTERVALS

class Repository:
    """
    Repozytorium odpowiedzialne za pobieranie danych ze zdalnego API
    i synchronizację ich z lokalną bazą danych.

    Metody w klasie zapewniają:
      - aktualizację listy stacji,
      - pobieranie widoku listy stacji,
      - pobieranie i aktualizację szczegółowych danych jakości powietrza dla konkretnej stacji.
    """

    def __init__(self, api_client: APIClient, database_client: DatabaseClient):
        """
        Inicjalizuje instancję repozytorium.

        Args:
            api_client (api.Client): Klient do komunikacji z zewnętrznym API.
            database_client (database.Client): Klient do operacji na lokalnej bazie danych.
        """
        self._api_client = api_client
        self._database_client = database_client

    def clone(self):
        return Repository(self._api_client,DatabaseClient(self._database_client.filepath))

    # Ta fukcja nie jest prywatna poniewaz moze sluzyc do odswierzenia
    def update_stations(self):
        """
        Pobiera aktualną listę stacji z API i zapisuje ją w bazie danych.

        Sekwencja działań:
          1. Wywołanie `fetch_stations()` na kliencie API.
          2. Przekazanie pobranych danych do `update_stations()` klienta bazy.
        """
        api_stations = self._api_client.fetch_stations()
        self._database_client.update_stations(
            stations=api_stations
        )

    def get_station_list_view(self) -> list[views.StationListView]:
        """
        Zwraca widok listy stacji, odświeżając dane jeśli upłynął zdefiniowany interwał.

        Jeśli od ostatniej aktualizacji minął czas określony w `UPDATE_INTERVALS['station']`,
        następuje wywołanie `update_stations()`.

        Returns:
            list[database.views.StationListView]: Lista obiektów widoku stacji.
        """
        last_update_at = self._database_client.get_last_stations_update()
        elapsed = datetime.now() - last_update_at

        if elapsed >= UPDATE_INTERVALS['station']:
            self.update_stations()

        return self._database_client.get_station_list_view()

    def fetch_station_details_view(self, station_id: int) -> views.StationDetailsView:
        return self._database_client.fetch_station_detail_view(station_id)

    # Ta fukcja nie jest prywatna poniewaz moze sluzyc do odswierzenia
    def update_station_air_quality_indexes(self, station_id: int):
        """
        Pobiera i aktualizuje wskaźniki jakości powietrza dla danej stacji.

        Args:
            station_id (int): Identyfikator stacji.
        """
        air_quality_indexes = self._api_client.fetch_air_quality_indexes(station_id)

        self._database_client.update_station_air_quality_indexes(
            station_id=station_id,
            indexes=air_quality_indexes
        )

    def fetch_station_air_quality_index_value(self, station_id: int,type_codename: str) -> int:
        """
        Zwraca listę wskaźników jakości powietrza, odświeżając dane
        gdy minął określony interwał czasu.

        Args:
            station_id (int): Identyfikator stacji.

        Returns:
            list[database.views.AQIndexView]: Lista obiektów widoku wskaźników jakości powietrza.
        """
        last_update_at = self._database_client.fetch_last_station_air_quality_indexes_update(station_id)
        elapsed = datetime.now() - last_update_at

        if elapsed >= UPDATE_INTERVALS['aq_indexes']:
            self.update_station_air_quality_indexes(station_id)

        return self._database_client.fetch_station_air_quality_index_value(station_id, type_codename)

    def update_station_sensors(self,station_id: int):
        stations = self._api_client.fetch_station_sensors(station_id)
        self._database_client.update_station_sensors(station_id, stations)

    def fetch_station_sensors(self,station_id: int) -> list[views.SensorView]:
        last_update_at = self._database_client.fetch_last_station_sensors_update(station_id)
        elapsed = datetime.now() - last_update_at

        if elapsed >= UPDATE_INTERVALS['sensors']:
            self.update_station_sensors(station_id)

        return self._database_client.fetch_station_sensors(station_id)
