from app import App
import logging

def main():

    app = App()
    app.run()


if __name__ == "__main__":
    logging.basicConfig(level='DEBUG')
    main()