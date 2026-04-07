# TODO logging
import sqlite3 as sqlite
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel


class Egg(BaseModel):
    egg_id: str
    name: str
    hint: str
    author: str
    max_redeems: int
    redeems: int
    created_at: str
    texture: bytes

class DB:
    """sqlite3 database management class"""

    __INIT_SQL_QUERY__ = """
                         CREATE TABLE IF NOT EXISTS eyren
                         (
                             id          TEXT PRIMARY KEY,
                             name        TEXT    NOT NULL,
                             hint        TEXT    NOT NULL,
                             author      TEXT    NOT NULL,
                             max_redeems INTEGER NOT NULL DEFAULT 1,
                             redeems     INTEGER NOT NULL DEFAULT 0,
                             created_at  TEXT             DEFAULT CURRENT_TIMESTAMP,
                             texture     BLOB
                         );
                         """

    __EGG_INSERT_QUERY__ = """
                           INSERT INTO eyren
                           (id,
                            name,
                            hint,
                            author,
                            max_redeems,
                            texture)
                           VALUES (?, ?, ?, ?, ?, ?);
                           """

    __GET_EGGS_QUERY__ = """
                         SELECT id,
                                name,
                                hint,
                                author,
                                max_redeems,
                                redeems,
                                created_at,
                                texture
                         FROM eyren
                         WHERE id = (?);
                         """

    __INCREMENT_REDEEM_QUERY__ = """
                                 UPDATE eyren
                                 SET redeems = redeems + 1
                                 WHERE id = (?)
                                   AND redeems < max_redeems;"""
    __GET_REDEEM_QUERY__ = """SELECT changes() > 0 AS success;"""

    __DELETE_EGG_QUERY__ = f"""
                           DELETE
                           FROM eyren
                           WHERE id = (?);"""

    path: str | Path
    name: str
    conn: sqlite.Connection
    cursor: sqlite.Cursor

    def __init__(self, db_name: str) -> None:
        self.path = db_name
        self.conn = sqlite.connect(db_name)
        self.conn.execute(self.__INIT_SQL_QUERY__)
        self.cursor = self.conn.cursor()

    def add_egg(
            self,
            name: str,
            hint: str,
            author: str,
            texture: bytes | str,
            max_redeems: int = 1,
    ) -> str:
        """Adds an egg to the database, returns id of the egg"""
        if not isinstance(texture, bytes):
            texture: bytes = Path(texture).read_bytes()

        egg_id = sha256(
            name.encode() + \
            hint.encode() + \
            author.encode() + \
            texture + \
            str(max_redeems).encode(),
        ).hexdigest()
        try:
            self.conn.execute(
                self.__EGG_INSERT_QUERY__,
                (egg_id, name, hint, author, max_redeems, texture),
            )
            self.conn.commit()
        except sqlite.IntegrityError:
            pass
        else:
            pass
        return egg_id

    def get_egg(self, egg_id: str) -> Egg:
        ret = self.conn.execute(self.__GET_EGGS_QUERY__, (egg_id,)).fetchone()

        return Egg(
            egg_id=ret[0],
            name=ret[1],
            hint=ret[2],
            author=ret[3],
            max_redeems=ret[4],
            redeems=ret[5],
            created_at=ret[6],
            texture=ret[7],
        )

    def redeem_egg(self, egg_id: str) -> bool:
        try:
            self.conn.execute(self.__INCREMENT_REDEEM_QUERY__, (egg_id,))
            return self.conn.execute(self.__GET_REDEEM_QUERY__).fetchone()
        except sqlite.OperationalError:
            raise ValueError("Egg not found")
        
    def delete_egg(self, egg_id: str) -> None:
        """Deletes an egg from the database"""
        try:
            self.conn.execute(self.__DELETE_EGG_QUERY__, (egg_id,))
            self.conn.commit()
        except sqlite.OperationalError:
            raise ValueError("Egg not found")