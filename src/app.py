import tkinter as tk
import tkinter.ttk as ttk

import api.client as api
import database.client as database
import repository

from gui.station_select import StationSelectFrame

class App:
    station_select: StationSelectFrame

    def __init__(self,root : tk.Tk = tk.Tk()):
        self.root = root
        self.root.title("DaVinciProject")
        self.root.geometry("800x400")
        api_client = api.Client()
        database_client = database.Client("database.db")

        self.repository = repository.Repository(api_client,database_client)



    def run(self):
        self.station_select = StationSelectFrame(
            master=self.root,
            repository=self.repository
        )
        self.station_select.pack(fill='both',expand=True)

        self.root.mainloop()