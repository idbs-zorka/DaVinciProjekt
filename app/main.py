import api.client as api
import database.client as db
import app.repository as repo
import logging
import app.gui.station_select as gui
import ttkthemes
import tkinter

def main():
    api_client = api.Client()
    db_client = db.Client("database.db")

    repository = repo.Repository(api_client,db_client)

    stations = repository.get_station_list_view()

    root = tkinter.Tk()

    style = ttkthemes.ThemedStyle(root)
    style.set_theme('black')

    root.title("Wybór stacji")
    root.geometry("800x400")
    root.minsize(width=600,height=300)
    gui.StationSelectFrame(root, repository).pack(fill='both', expand=True)
    root.mainloop()


def main2():
    api_client = api.Client()
    db_client = db.Client("database.db")

    print("Reading station lists..")

    repository = repo.Repository(api_client,db_client)

    stations = repository.get_station_list_view()

    for station in stations:
        print(station)

    while True:
        station_id = int(input("Station id:")) # 190
        for index in repository.fetch_station_air_quality_indexes(station_id):
            print(index)

if __name__ == "__main__":
    logging.basicConfig(level='DEBUG')
    main()