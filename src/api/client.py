from datetime import datetime
from typing import Callable, Any

import requests

import src.api.exceptions as exceptions
import src.api.models as models


class Client:
    """
    Klient HTTP dla GIOŚ-owego API (https://api.gios.gov.pl),
    obsługujący paginację, błędy oraz mapowanie odpowiedzi na modele.
    """

    __BASE = "https://api.gios.gov.pl"

    def make_url(
        self,
        endpoint: str,
        page: int = 0,
        size: int = 100,
        args: dict[str, Any] = None
    ) -> str:
        """
        Buduje pełny URL z bazowego adresu, ścieżki, parametrów paginacji i opcjonalnych argumentów.

        Args:
            endpoint (str): Ścieżka API (np. "pjp-api/v1/rest/station/findAll").
            page (int, opcjonalnie): Numer strony (0–based). Domyślnie 0.
            size (int, opcjonalnie): Maksymalna liczba rekordów na stronę. Domyślnie 100.
            args (dict[str, Any], opcjonalnie): Dodatkowe pary klucz=wartość do doklejenia w query string.

        Returns:
            str: Pełny adres URL gotowy do wywołania przez `requests.get()`.
        """
        if args is None:
            args = {}
        url = f"{self.__BASE}/{endpoint}?page={page}&size={size}"
        for arg, val in args.items():
            url += f"&{arg}={val}"
        return url

    def __get(
        self,
        endpoint: str,
        page: int = 0,
        size: int = 100,
        args: dict[str, Any] = None
    ) -> Any:
        """
        Wykonuje pojedyncze żądanie GET, sprawdza status i zwraca zdeserializowane JSON.

        Args:
            endpoint (str): Ścieżka API.
            page (int, opcjonalnie): Numer strony.
            size (int, opcjonalnie): Rozmiar strony.
            args (dict[str, Any], opcjonalnie): Dodatkowe argumenty query.

        Returns:
            Any: Słownik lub lista wyników z odpowiedzi JSON.

        Raises:
            exceptions.APIError: W przypadku błędu HTTP, z mapowaniem pola
                `error_code`, `error_reason`, `error_result`, `error_solution`.
        """
        try:
            url = self.make_url(endpoint, page, size, args)
            response = requests.get(url,timeout=None)
            response.raise_for_status() # Sprawdzanie bledow po stronie serwera
            return response.json()
        except requests.exceptions.HTTPError as e:
            payload = e.response.json()
            raise exceptions.APIError(
                code=payload["error_code"],
                reason=payload["error_reason"],
                result=payload["error_result"],
                solution=payload["error_solution"]
            )

    def __get_collected(
        self,
        endpoint: str,
        target: str, # Glowna wartosc zapytania json
        args: dict[str, Any] = None
    ) -> Any:
        """
        Pobiera wszystkie strony wyników (paginacja) i scala dane z pola `target`.

        Args:
            endpoint (str): Ścieżka API.
            target (str): Klucz w JSON, pod którym znajdują się dane (lista lub dict).
            args (dict[str, Any], opcjonalnie): Dodatkowe argumenty query.

        Returns:
            list|dict: Scalona lista lub słownik wyników.

        Raises:
            TypeError: Jeśli zwrócony fragment JSON nie jest ani listą, ani słownikiem.
        """
        response = self.__get(endpoint, args=args)
        total_pages = int(response['totalPages']) # Odczyt ilosci stron zapytan. Zmienna na koncu pierwszej strony zapytania
        fragment = response[target] # Wartosc glownego elementu zapytania

        if isinstance(fragment, list):
            result = list(fragment)
        elif isinstance(fragment, dict):
            result = dict(fragment)
        else:
            raise TypeError(f"Unexpected target type: {type(fragment).__name__}")

        for page in range(1, total_pages):
            response = self.__get(endpoint, page=page, args=args)
            fragment = response[target]
            if isinstance(fragment, list):
                result.extend(fragment)
            elif isinstance(fragment, dict):
                result.update(fragment)
            else:
                raise TypeError(f"Unexpected target type: {type(fragment).__name__}")

        return result
    # Opcjonalna optymalizacja
    def __get_each(
        self,
        endpoint: str,
        target: str,
        callback: Callable[[Any], None],
        args: dict[str, Any] = None
    ) -> None:
        """
        Iteruje po stronach wyników i wywołuje `callback` dla każdego fragmentu `target`.

        Args:
            endpoint (str): Ścieżka API.
            target (str): Klucz JSON, z którego pobiera fragment.
            callback (Callable[[Any], None]): Funkcja wywoływana z fragmentem danych.
            args (dict[str, Any], opcjonalnie): Dodatkowe argumenty query.
        """
        response = self.__get(endpoint, args=args)
        total_pages = int(response['totalPages'])

        for page in range(total_pages):
            if page > 0:
                response = self.__get(endpoint, page=page, args=args)
            callback(response[target])

    def fetch_stations(self) -> list[models.Station]:
        """
        Pobiera pełną listę stacji pomiarowych ze scalam paginację.

        Returns:
            list[models.Station]: Lista obiektów Station z danymi o lokalizacji i nazewnictwie.
        """
        raw = self.__get_collected(
            endpoint="pjp-api/v1/rest/station/findAll",
            target="Lista stacji pomiarowych"
        )
        return [
            models.Station(
                id=entry["Identyfikator stacji"],
                codename=entry["Kod stacji"],
                name=entry["Nazwa stacji"],
                district=entry["Powiat"],
                voivodeship=entry["Województwo"],
                city=entry["Nazwa miasta"],
                address=entry["Ulica"],
                latitude=entry["WGS84 φ N"],
                longitude=entry["WGS84 λ E"]
            )
            for entry in raw
        ]

    def fetch_station_meta(
        self,
        city: str = None,
        station_codename: str = None
    ) -> list[models.StationMeta]:
        """
        Pobiera metadane (kody międzynarodowe, daty otwarcia/zamknięcia, typ)
        dla stacji, filtrowane opcjonalnie po mieście lub kodzie stacji.

        Args:
            city (str, opcjonalnie): Nazwa miasta do filtrowania.
            station_codename (str, opcjonalnie): Kod stacji do filtrowania.

        Returns:
            list[models.StationMeta]: Lista obiektów StationMeta.
        """

        params = dict()

        if city is not None:
            params.update({"miasto": city})

        if station_codename is not None:
            params.update({"kod-stacji": station_codename})

        raw = self.__get_collected(
            endpoint="pjp-api/v1/rest/metadata/stations",
            target="Lista metadanych stacji pomiarowych",
            args=params
        )
        return [
            models.StationMeta(
                codename=entry["Kod stacji"],
                international_codename=entry["Kod międzynarodowy"],
                launch_date=datetime.fromisoformat(entry["Data uruchomienia"]),
                close_date=(
                    datetime.fromisoformat(entry["Data zamknięcia"])
                    if entry["Data zamknięcia"] is not None else None
                ),
                type=entry["Rodzaj stacji"]
            )
            for entry in raw
        ]

    def fetch_air_quality_indexes(
        self,
        station_id: int
    ) -> models.AirQualityIndexes:
        """
        Pobiera aktualne indeksy jakości powietrza dla stacji,
        zarówno ogólny, jak i dla poszczególnych sensorów.

        Args:
            station_id (int): Identyfikator stacji pomiarowej.

        Returns:
            models.AirQualityIndexes | None: Obiekt z wartościami indeksów
            lub None, jeśli dla stacji nie ma aktualnych danych.

        Raises:
            ValueError: Jeśli odpowiedź API ma niespodziewany format.
        """
        raw = self.__get_collected(
            endpoint=f"pjp-api/v1/rest/aqindex/getIndex/{station_id}",
            target="AqIndex"
        )

        # Jezeli nie ma podanego czasu to zwraca None uproszczenia czytelnosci
        get_date = lambda key: datetime.fromisoformat(raw[key]) if (raw[key] is not None) else None

        # Dla wartosci ogolnej
        overall = models.Index(
            date=get_date("Data wykonania obliczeń indeksu"),
            value=raw["Wartość indeksu"]
        )
        # Dla poszczegolnych wartosci
        sensors: dict[str, models.Index] = {
            pollutant: models.Index(
                date=get_date(f"Data wykonania obliczeń indeksu dla wskaźnika {pollutant}"),
                value=raw[f"Wartość indeksu dla wskaźnika {pollutant}"]
            )
            for pollutant in ['NO2', 'O3', 'PM10', 'PM2.5', 'SO2']
        }

        return models.AirQualityIndexes(
            overall=overall,
            sensors=sensors,
            index_status=raw["Status indeksu ogólnego dla stacji pomiarowej"],
            index_critical=raw["Kod zanieczyszczenia krytycznego"]
        )

    def fetch_station_sensors(self,station_id: int) -> list[models.Sensor]:
        raw = self.__get_collected(
            endpoint=f"pjp-api/v1/rest/station/sensors/{station_id}",
            target="Lista stanowisk pomiarowych dla podanej stacji"
        )

        return [
            models.Sensor(
                id=raw['Identyfikator stanowiska'],
                codename=raw['Wskaźnik - kod'],
                name=raw['Wskaźnik']
            )
        ]

    def fetch_sensor_data(self,sensor_id: int) -> list[models.SensorData]:
        result: list[models.SensorData] = []

        def collect_data(data):
            result.extend(
                SensorDataView(
                    date=datetime.fromisoformat(entry['Data']),
                    value=entry['Wartość']
                ) for entry in data
            )

        self.__get_each(
            endpoint=f"pjp-api/v1/rest/data/getData/{sensor_id}",
            target=f"Lista danych pomiarowych",
            callback=collect_data
        )

        return result