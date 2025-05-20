import dataclasses
import tkinter as tk
from tkinter import ttk

import tkintermapview
from tkintermapview import TkinterMapView
from tkintermapview.canvas_position_marker import CanvasPositionMarker

from src.database.views import StationListView
import src.location as location
import src.config as config
from typing import Callable, List, Optional, Any

from src.repository import Repository
from dataclasses import dataclass

from src.fuzzy_seach import fuzzy_search


@dataclass
class FilterState:
    city: str | None
    search_query: str | None

class TkinterMapViewExtended(tkintermapview.TkinterMapView):

    def get_bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        #TODO: Doesn't work
        """
        Returns ((lat_top, lon_left), (lat_bottom, lon_right))
        for the currently visible map area, using the stored
        upper_left_tile_pos and lower_right_tile_pos.
        """
        self.update_idletasks()
        # these are fractional tile coords stored on the widget
        ul_x, ul_y = self.upper_left_tile_pos
        lr_x, lr_y = self.lower_right_tile_pos
        zoom = int(self.zoom)  # current integer zoom level

        # convert upper-left tile to lat/lon
        lat_ul, lon_ul = tkintermapview.osm_to_decimal(ul_x, ul_y, zoom)
        # convert lower-right tile to lat/lon
        lat_lr, lon_lr = tkintermapview.osm_to_decimal(lr_x, lr_y, zoom)

        return (lat_ul, lon_ul), (lat_lr, lon_lr)


class SearchBarFrame(ttk.Frame):
    """
    Frame containing a search label and entry.
    """
    DEFAULT_CITY_COMBOBOX_VALUE = "Wybierz miasto"

    def __init__(self, master: tk.Misc, cities: list[str], on_filter: Optional[Callable[[FilterState], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_filter = on_filter


        ttk.Label(self, text="Szukaj:").grid(
            row=0, column=0,
            padx=5, pady=5
        )

        self.search_entry = ttk.Entry(self)
        self.search_entry.grid(
            row=0, column=1,
            padx=5, pady=5,
            sticky='ew',
        )
        self.search_entry.bind('<KeyRelease>', self._on_filter_changed)

        ttk.Label(self, text="Miasto:").grid(
            row=1, column=0,
        )

        self.city_choice = ttk.Combobox(
            self,
            values=[self.DEFAULT_CITY_COMBOBOX_VALUE,*cities],
            state='readonly'
        )
        self.city_choice.current(0)

        self.city_choice.grid(
            row=1, column=1,
            padx=5,pady=5,
            sticky='ew',
        )
        self.city_choice.bind('<<ComboboxSelected>>',self._on_filter_changed)


    def _on_filter_changed(self, event: tk.Event):
        current_city = self.city_choice.get().strip()

        if current_city == '' or current_city == self.DEFAULT_CITY_COMBOBOX_VALUE:
            current_city = None

        current_search_query = self.search_entry.get().strip()

        if current_search_query == '':
            current_search_query = None

        self.on_filter(
            FilterState(
                city=current_city,
                search_query=current_search_query
            )
        )


class StationListFrame(ttk.Frame):
    """
    Frame with a Listbox to display station names.
    """

    def __init__(
        self,
        master: tk.Misc,
        stations: List[str],
        on_select: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_select = on_select

        self.list_var = tk.StringVar(value=stations)
        self.listbox = tk.Listbox(self, listvariable=self.list_var)
        self.listbox.pack(fill='both', expand=True,padx=5,pady=5)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

    def set_items(self, items: List[str]) -> None:
        """Update the list of stations."""
        self.list_var.set(items)

    def set_selected_item(self, item: str) -> None:
        """Select and scroll to the given station name."""
        try:
            index = self.listbox.get(0, tk.END).index(item)
        except ValueError:
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.see(index)

    def get_selected_item(self) -> Optional[str]:
        """Return the currently selected station name, or None."""
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.listbox.get(sel[0])

    def _on_select(self, event: tk.Event):
        item = self.get_selected_item()
        if item:
            self.on_select(item)


class StationSelectFrame(ttk.Frame):
    """
    Main frame combining search bar, station list, and map view.
    """

    def __init__(
        self,
        master: tk.Misc,
        repository: Repository,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.repository = repository
        self.stations = self.repository.get_station_list_view()
        self.filtered_stations = self.stations

        self._build_layout()

    def _build_layout(self) -> None:
        left = ttk.Frame(self)
        left.pack(side='left', fill='y', padx=2, pady=2)
        left.config(borderwidth=2, relief='groove')

        cities = list(set(station.city for station in self.stations))
        cities.sort()

        self.search_bar = SearchBarFrame(
            left,
            cities=cities,
            on_filter=self._filter_stations)
        self.search_bar.pack(fill='x', pady=(0, 4))

        self.station_list = StationListFrame(
            left, stations=[st.name for st in self.stations], on_select=self._on_station_select
        )
        self.station_list.pack(fill='both', expand=True)

        right = ttk.Frame(self)
        right.pack(side='right', fill='both', expand=True, padx=2, pady=2)
        right.config(borderwidth=2, relief='groove')
        right.columnconfigure((0, 1, 2, 3), weight=1)
        right.rowconfigure(1, weight=1)

        index_input_frame = ttk.Frame(right)
        index_input_frame.pack(side='top')
        index_input_frame.columnconfigure(0,weight=1)
        ttk.Label(index_input_frame, text="Typ indeksu:").grid(row=0,column=1)

        self.index_cb = ttk.Combobox(
            index_input_frame,
            values=config.AQ_TYPES,
            state='readonly',
        )
        self.index_cb.grid(row=0,column=2)
        self.index_cb.bind('<<ComboboxSelected>>', self._on_index_change)
        self.index_cb.current(0)

        self.map = TkinterMapViewExtended(
            right,
            database_path="offline_map_data.db"
        )
        self.map.pack(side='bottom', fill='both',expand=True)

        self._setup_markers()
        self._set_default_position()


    def _setup_markers(self) -> None:
        self.map.delete_all_marker()

        #TODO: Filter by visible markers

        for station in self.filtered_stations:
            indexes = self.repository.fetch_station_air_quality_indexes(station.id)
            target_index = self.index_cb.get()
            try:
                current_index_value = next(idx.value for idx in indexes if idx.codename == target_index)
                color = config.AQ_INDEX_CATEGORIES_COLORS[current_index_value]

                self.map.set_marker(
                    deg_x=station.latitude,
                    deg_y=station.longitude,
                    text=station.name,
                    marker_color_circle=color,
                    marker_color_outside=color,
                    command=self._on_marker_click
                )
            except StopIteration:
                pass

    def _set_default_position(self) -> None:
        pos = location.current_location() or (52.215933, 19.134422)
        self.map.set_position(deg_x=pos[0], deg_y=pos[1])

    def _on_station_select(self, name: str) -> None:
        """Center map on station selected from list."""
        station = next((s for s in self.stations if s.name == name), None)
        if station:
            self.map.set_position(deg_x=station.latitude, deg_y=station.longitude)

    def _on_marker_click(self, marker: CanvasPositionMarker) -> None:
        """When a map marker is clicked, select the corresponding list item and center map."""
        station: StationListView = marker.data
        self.map.set_position(deg_x=marker.position[0], deg_y=marker.position[1])
        self.station_list.set_selected_item(station.name)

    def _filter_stations(self, filter_state: FilterState) -> None:
        """Filter the list of stations by name or city."""


        self.filtered_stations = [
            st for st in self.stations
            if st.city == filter_state.city
        ] if filter_state.city is not None else self.stations

        if filter_state.search_query is not None:
            name_to_station = {st.name: st for st in self.filtered_stations}
            searched = fuzzy_search(
                query=filter_state.search_query,
                choice=[st.name for st in self.filtered_stations],
                score_cutoff=60
            )
            self.filtered_stations = [
                name_to_station[name]
                for name in searched
            ]

        self.station_list.set_items([st.name for st in self.filtered_stations])

    def _on_filter_change(self,filter_state: FilterState):
        self._filter_stations(filter_state)
        self._setup_markers()

    def _on_index_change(self, event: tk.Event) -> None:
        self._setup_markers()
