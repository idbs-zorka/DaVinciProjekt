import src.api.client as api
import src.database.client as database
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

    def __init__(self, api_client: api.Client, database_client: database.Client):
        """
        Inicjalizuje instancję repozytorium.

        Args:
            api_client (api.Client): Klient do komunikacji z zewnętrznym API.
            database_client (database.Client): Klient do operacji na lokalnej bazie danych.
        """
        self._api_client = api_client
        self._database_client = database_client

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

    def get_station_list_view(self) -> list[database.views.StationListView]:
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

    def fetch_station_details_view(self, station_id: int) -> database.views.StationDetailsView:
        """
        Pobiera szczegółowe dane widoku dla wybranej stacji.

        Args:
            station_id (int): Identyfikator stacji.

        Returns:
            database.views.StationDetailsView: Obiekt widoku ze szczegółami stacji.

        Raises:
            ValueError: Jeśli nie znaleziono stacji o podanym identyfikatorze.
        """
        # TODO: implementować logikę pobierania szczegółów stacji
        raise NotImplementedError("Metoda `fetch_station_details_view` nie została jeszcze zaimplementowana.")

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

    def fetch_station_air_quality_indexes(self, station_id: int) -> list[database.views.AQIndexView]:
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

        return self._database_client.fetch_station_air_quality_indexes(station_id)
