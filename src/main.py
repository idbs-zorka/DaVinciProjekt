from PySide6 import QtCore, QtWidgets, QtGui
from gui.station_select import *
import sys,random,logging

def main():
    app = QtWidgets.QApplication([])

    widget = StationSelectWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())



if __name__ == "__main__":
    logging.basicConfig(level='DEBUG')
    main()