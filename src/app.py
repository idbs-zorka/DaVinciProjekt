import tkinter as tk
import tkinter.ttk as ttk

import api.client as api
import database.client as database
import repository

from gui.station_select import StationSelectFrame,StationDetailsFrame


class App:
    station_select_frame: StationSelectFrame
    station_details_frame: StationDetailsFrame = None

    def __init__(self,root : tk.Tk = tk.Tk()):
        self.root = root
        self.root.title("DaVinciProject")
        self.root.geometry("800x400")
        api_client = api.Client()
        database_client = database.Client("database.db")

        self.repository = repository.Repository(api_client,database_client)

    def run(self):
        self.station_select_frame = StationSelectFrame(
            master=self.root,
            repository=self.repository,
            on_station_select=lambda target_id: self.open_details(target_id)
        )
        self.station_select_frame.pack(fill='both', expand=True)

        self.root.mainloop()

    def open_details(self,station_id: int):
        if self.station_details_frame is not None:
            if self.station_details_frame.target_station_id != station_id:
                self.station_details_frame.destroy()

        details = self.repository.fetch_station_details_view(station_id)
        self.station_details_frame = StationDetailsFrame(details)