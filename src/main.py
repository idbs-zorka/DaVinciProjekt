import logging
from app import Application

from database.client import Client as DatabaseClient
from api.client import Client as APIClient
from repository import Repository

def main():
    database_client = DatabaseClient("database.db")
    api_client = APIClient()

    repository = Repository(api_client, database_client)

    app = Application(repository)

    app.run()

if __name__ == "__main__":
    logging.basicConfig(level='DEBUG')
    main()