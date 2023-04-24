from _db import database
from settings import CONFIG


def main():
    tables = CONFIG.INSERT.keys()
    for table in tables:
        database.delete_from(table=table)


if __name__ == "__main__":
    main()
