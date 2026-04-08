# TODO logging
import random
import sqlite3 as sqlite
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel
import dotenv

SALT = "abc"# str(dotenv.dotenv_values(".env")["SALT"])
assert SALT is not None, "SALT is not set"


class Egg(BaseModel):
    egg_id: str
    name: str
    hint: str
    author: str
    max_redeems: int
    redeems: int
    created_at: str
    texture: str


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
                             redeemed_users TEXT DEFAULT '',
                             texture     TEXT
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

    __REDEEM_EGG_QUERY__ = """
                           UPDATE eyren
                           SET redeems        = redeems + 1,
                               redeemed_users =
                                   CASE
                                       WHEN redeemed_users = '' OR redeemed_users IS NULL
                                           THEN :user_id
                                       ELSE redeemed_users || ',' || :user_id
                                       END
                           WHERE id = :id
                             AND redeems < max_redeems
                             AND (
                               redeemed_users IS NULL
                                   OR redeemed_users = ''
                                   OR ',' || redeemed_users || ',' NOT LIKE '%,' || :user_id || ',%'
                               );
                           """

    __DELETE_EGG_QUERY__ = f"""
                           DELETE
                           FROM eyren
                           WHERE id = (?);"""

    __GET_USER_EGGS_QUERY__ = """
                              SELECT id,
                                name,
                                hint,
                                author,
                                max_redeems,
                                redeems,
                                created_at,
                                texture
                              FROM eyren
                              WHERE ',' || redeemed_users || ',' LIKE '%,' || (?) || ',%';
                              """

    path: str | Path
    name: str
    conn: sqlite.Connection

    def __init__(self, db_name: str) -> None:
        self.path = db_name
        self.conn = sqlite.connect(db_name)
        self.conn.execute(self.__INIT_SQL_QUERY__)
        self.conn.commit()
        self.conn.close()

    def __enter__(self,commit_after:bool=True):
        self.__commit_after = commit_after
        self.conn = sqlite.connect(self.path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__commit_after:
            self.conn.commit()
        self.conn.close()

    def add_egg(
        self,
        name: str,
        hint: str,
        author: str,
        texture: str, # base64 encoded
        max_redeems: int = 1,
    ) -> tuple[bool, str]:
        """Adds an egg to the database, returns whether egg was added and it's id"""


        egg_id = sha256(name.encode() + author.encode() + SALT.encode()).hexdigest()
        try:
            self.conn.execute(
                self.__EGG_INSERT_QUERY__,
                (egg_id, name, hint, author, max_redeems, texture),
            )
            self.conn.commit()
        except sqlite.IntegrityError:
            return False, egg_id
        else:
            pass
        return True, egg_id

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

    def redeem_egg(self,user_id: str|int, egg_id: str) -> bool:
        uid = str(user_id)
        try:
            before = self.conn.total_changes
            self.conn.execute(self.__REDEEM_EGG_QUERY__, {"id": egg_id, "user_id": uid})
            self.conn.commit()
            return self.conn.total_changes > before
        except sqlite.OperationalError:
            raise ValueError("Egg not found")

    def delete_egg(self, egg_id: str) -> None:
        """Deletes an egg from the database"""
        try:
            self.conn.execute(self.__DELETE_EGG_QUERY__, (egg_id,))
            self.conn.commit()
        except sqlite.OperationalError:
            raise ValueError("Egg not found")

    def list_eggs(self) -> list[Egg]:
        """Returns a list of all eggs in the database"""
        return [
            self.get_egg(egg_id)
            for (egg_id,) in self.conn.execute("SELECT id FROM eyren")
        ]

    def get_user_eggs(self, user_id: str) -> list[Egg]:
        """Returns a list of all eggs in the database"""
        try:
            user_eggs = []
            eggs = self.conn.execute(self.__GET_USER_EGGS_QUERY__, (user_id,)).fetchall()
            for egg_info in eggs:
                user_eggs.append(
                    Egg(
                        egg_id=egg_info[0],
                        name=egg_info[1],
                        hint=egg_info[2],
                        author=egg_info[3],
                        max_redeems=egg_info[4],
                        redeems=egg_info[5],
                        created_at=egg_info[6],
                        texture=egg_info[7],
                    )
                )
            return user_eggs
        except sqlite.OperationalError:
            raise ValueError("User not found")


if __name__ == "__main__":
    db = DB("db.db")
    print(
        "added",
        db.add_egg(
            name="Evil Egg",
            hint="Commit some war crimes",
            author="Gay Lord",
            texture=random.randbytes(1024).decode(),
        ),
    )

    print(
        "added",
        db.add_egg(
            name="Test Egg",
            hint="do some testing",
            author="Test",
            texture=random.randbytes(1024).decode(),
        ),
    )

    print(
        "added",
        db.add_egg(
            name="Chicken Egg",
            hint="Bok Bok",
            author="Hen",
            texture=random.randbytes(1024).decode(),
        ),
    )

    for e in db.list_eggs():
        print(e.name)

    print(db.redeem_egg("3211","8b9507c8d29347f8be1c3fbd2d0533e9"))
    print("===")
    print(*[x.name for x in db.get_user_eggs("1")],sep='\n')