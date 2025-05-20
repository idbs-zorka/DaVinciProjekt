import sys
import logging
from app import Application

def main():
    app = Application()
    app.exec()

if __name__ == "__main__":
    logging.basicConfig(level='DEBUG')
    main()