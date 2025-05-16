import tkinter as tk
from tkinter import ttk
from tkintermapview import TkinterMapView
from tkintermapview.canvas_position_marker import CanvasPositionMarker

from app.database.views import StationListView
import app.location as location
import app.config as config
from typing import Callable, List, Optional

from app.repository import Repository


class SearchBarFrame(ttk.Frame):
    """
    Frame containing a search label and entry.
    """

    def __init__(self, master: tk.Misc, on_search: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_search = on_search

        ttk.Label(self, text="Szukaj:").pack(side='left', padx=(0, 4))
        self.entry = ttk.Entry(self)
        self.entry.pack(side='right', fill='x', expand=True)
        self.entry.bind('<KeyRelease>', self._handle_search)

    def _handle_search(self, event: tk.Event):
        if self.on_search:
            query = self.entry.get().strip()
            self.on_search(query)


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
        self.listbox.pack(fill='both', expand=True)
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
        self.display_names = [st.name for st in self.stations]

        self._build_layout()

    def _build_layout(self) -> None:
        left = ttk.Frame(self)
        left.pack(side='left', fill='y', padx=2, pady=2)
        left.config(borderwidth=2, relief='groove')

        self.search_bar = SearchBarFrame(left, on_search=self._filter_stations)
        self.search_bar.pack(fill='x', pady=(0, 4))

        self.station_list = StationListFrame(
            left, stations=self.display_names, on_select=self._on_station_select
        )
        self.station_list.pack(fill='both', expand=True)

        right = ttk.Frame(self)
        right.pack(side='right', fill='both', expand=True, padx=2, pady=2)
        right.config(borderwidth=2, relief='groove')
        right.columnconfigure((0, 1, 2, 3), weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="Miasto:").grid(row=0, column=0, sticky=tk.W)
        cities = sorted({st.city for st in self.stations})
        self.city_cb = ttk.Combobox(right, values=cities, state='readonly')
        self.city_cb.grid(row=0, column=1, sticky=tk.EW)
        self.city_cb.bind('<<ComboboxSelected>>', self._on_city_change)

        ttk.Label(right, text="Typ indeksu:").grid(row=0, column=2, sticky=tk.W)
        self.index_cb = ttk.Combobox(
            right,
            values=config.AQ_TYPES,
            state='readonly',
        )
        self.index_cb.grid(row=0, column=3, sticky=tk.EW)
        self.index_cb.bind('<<ComboboxSelected>>', self._on_index_change)
        self.index_cb.current(0)
        self.map = TkinterMapView(
            right,
            database_path="offline_map_data.db"
        )
        self.map.grid(row=1, column=0, columnspan=4, sticky='nsew')

        self._init_markers()
        self._set_default_position()

    def _init_markers(self) -> None:
        for st in self.stations:
            self.map.set_marker(
                deg_x=st.latitude,
                deg_y=st.longitude,
                text=st.name,
                command=self._on_marker_click,
                data=st,
            )

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

    def _filter_stations(self, query: str) -> None:
        """Filter the list of stations by name or city."""
        filtered = [st.name for st in self.stations if query.lower() in st.name.lower()]
        self.station_list.set_items(filtered)

    def _on_filter_change(self,event: tk.Event):
        city = self.city_cb.get()
        if city == '':
            city = None

        index_type = self.index_cb.get()
        self.set_station_map_markers(city,index_type)

    def _on_city_change(self, event: tk.Event) -> None:
        self._on_filter_change(event)

    def _on_index_change(self, event: tk.Event) -> None:
        self._on_filter_change(event)

    def set_station_map_markers(
        self,
        city: Optional[str] = None,
        aq_index_type: Optional[str] = None,
    ) -> None:
        """
        Show markers only for stations matching city and/or index type.
        """
        # Clear existing markers
        self.map.delete_all_marker()

        # Filter stations
        filtered = [s for s in self.stations if (city is None or s.city == city)]


        aq_indexes = [
            (
                station,
                {
                    idx.codename: idx.value
                    for idx in self.repository.fetch_station_air_quality_indexes(station.id)
                }
            )
            for station in filtered
        ]

        # Recreate markers
        for (st,idx) in aq_indexes:
            value = idx[aq_index_type]
            color = config.AQ_INDEX_CATEGORIES_COLORS[value]

            self.map.set_marker(
                deg_x=st.latitude,
                deg_y=st.longitude,
                text=st.name,
                marker_color_circle=color,
                command=self._on_marker_click,
                data=st
            )