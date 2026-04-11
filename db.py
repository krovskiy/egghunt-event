# TODO logging
import sqlite3 as sqlite
import typing
from hashlib import sha256
from pathlib import Path

import dotenv
from pydantic import BaseModel

SALT = str(dotenv.dotenv_values(".env")["SALT"])
assert SALT is not None, "SALT is not set"  # noqa: S101


class DBError(Exception):
    pass


class Egg(BaseModel):
    egg_id: str
    name: str
    hint: str
    author_id: str
    author: str
    author_avatar: str
    max_redeems: int
    redeems: int
    created_at: str
    texture: str
    textureSize: int


class DB:
    """sqlite3 database management class"""

    __INIT_SQL_QUERY__ = """
                         CREATE TABLE IF NOT EXISTS eyren
                         (
                             id          TEXT PRIMARY KEY,
                             name        TEXT    NOT NULL,
                             hint        TEXT    NOT NULL,
                             author_id   TEXT    NOT NULL,
                             author      TEXT    NOT NULL,
                             author_avatar    TEXT    NOT NULL DEFAULT '',
                             max_redeems INTEGER NOT NULL DEFAULT 1,
                             redeems     INTEGER NOT NULL DEFAULT 0,
                             created_at  TEXT             DEFAULT CURRENT_TIMESTAMP,
                             redeemed_users TEXT DEFAULT '',
                             texture     TEXT,
                             textureSize INTEGER NOT NULL DEFAULT 0,
                             liked_users       TEXT,
                             disliked_users    TEXT
                         );
                         """

    __LIKE_EGG_QUERY__ = """
                        UPDATE eyren
                        SET liked_users =
                            CASE
                                WHEN liked_users = '' OR liked_users IS NULL
                                    THEN :user_id
                                ELSE liked_users || ',' || :user_id
                            END
                        WHERE id = :id
                          AND (
                              liked_users IS NULL
                                  OR liked_users = ''
                                  OR ',' || liked_users || ',' NOT LIKE '%,' || :user_id || ',%'
                          )
                          AND (
                              disliked_users IS NULL
                                  OR disliked_users = ''
                                  OR ',' || disliked_users || ',' NOT LIKE '%,' || :user_id || ',%'
                          );
                        """

    __DISLIKE_EGG_QUERY__ = """
                           UPDATE eyren
                           SET disliked_users =
                               CASE
                                   WHEN disliked_users = '' OR disliked_users IS NULL
                                       THEN :user_id
                                   ELSE disliked_users || ',' || :user_id
                               END
                           WHERE id = :id
                             AND (
                                 disliked_users IS NULL
                                     OR disliked_users = ''
                                     OR ',' || disliked_users || ',' NOT LIKE '%,' || :user_id || ',%'
                             )
                             AND (
                                 liked_users IS NULL
                                     OR liked_users = ''
                                     OR ',' || liked_users || ',' NOT LIKE '%,' || :user_id || ',%'
                             );
                           """

    __EGG_INSERT_QUERY__ = """
                           INSERT INTO eyren
                           (id,
                            name,
                            hint,
                            author_id,
                            author,
                            author_avatar,
                            max_redeems,
                            texture,
                            textureSize)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                           """
    # new by dima - update egg with author and other stuff
    __EGG_UPDATE_QUERY__ = """
                                                    UPDATE eyren
                                                    SET name = ?,
                                                            hint = ?,
                                                            author = ?,
                                                            author_avatar = ?,
                                                            max_redeems = ?,
                                                            texture = ?,
                                                            textureSize = ?
                                                    WHERE id = ?
                                                        AND author_id = ?;
                                                    """

    __GET_EGGS_QUERY__ = """
                         SELECT id,
                                name,
                                hint,
                                author_id,
                                author,
                                author_avatar,
                                max_redeems,
                                redeems,
                                created_at,
                                texture,
                                textureSize
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
                             AND author_id != :user_id
                             AND redeems < max_redeems
                             AND (
                               redeemed_users IS NULL
                                   OR redeemed_users = ''
                                   OR ',' || redeemed_users || ',' NOT LIKE '%,' || :user_id || ',%'
                               );
                           """

    __DELETE_EGG_QUERY__ = """
                           DELETE
                           FROM eyren
                           WHERE id = (?);"""

    __GET_USER_EGGS_QUERY__ = """
                              SELECT id,
                                name,
                                hint,
                                author_id,
                                author,
                                author_avatar,
                                max_redeems,
                                redeems,
                                created_at,
                                texture,
                                textureSize
                              FROM eyren
                              WHERE ',' || redeemed_users || ',' LIKE '%,' || (?) || ',%';
                              """
    # new by dima update by texture size and other stuff
    __GET_CREATED_EGGS_QUERY__ = """
                                SELECT id,
                                    name,
                                    hint,
                                    author_id,
                                    author,
                                    author_avatar,
                                    max_redeems,
                                    redeems,
                                    created_at,
                                    texture,
                                    textureSize
                                FROM eyren
                                WHERE author_id = (?);
                                """

    path: str | Path
    conn: sqlite.Connection

    def __init__(self, db_name: str) -> None:
        self.path = db_name
        self.conn = sqlite.connect(db_name)
        self.conn.execute(self.__INIT_SQL_QUERY__)
        self._migrate(self.conn)
        self.conn.commit()
        self.conn.close()

    # i have no idea, some ai slop
    def _migrate(self, conn: sqlite.Connection) -> None:
        """Add new columns to existing databases that predate this schema."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(eyren)")}
        migrations = [
            ("author_id",     "ALTER TABLE eyren ADD COLUMN author_id     TEXT NOT NULL DEFAULT ''"),
            ("author_avatar", "ALTER TABLE eyren ADD COLUMN author_avatar TEXT NOT NULL DEFAULT ''"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(sql)

    def __enter__(self, commit_after: bool = True) -> typing.Self:
        try:
            self.__commit_after = commit_after
            self.conn = sqlite.connect(self.path)
        except sqlite.Error as e:
            raise DBError(e) from e
        else:
            return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if self.__commit_after:
            try:
                self.conn.commit()
            except sqlite.Error as e:
                raise DBError(e) from e
        self.conn.close()

    def _row_to_egg(self, row: tuple) -> "Egg":
        return Egg(
            egg_id=row[0],
            name=row[1],
            hint=row[2],
            author_id=row[3],
            author=row[4],
            author_avatar=row[5],
            max_redeems=row[6],
            redeems=row[7],
            created_at=row[8],
            texture=row[9],
            textureSize=row[10],
        )
    
    def add_egg(
        self,
        name: str,
        hint: str,
        author_id: str,
        author: str,
        author_avatar: str,
        texture: str,
        max_redeems: int = 1,
        textureSize: int = 0,
    ) -> tuple[bool, str]:
        """Adds an egg to the database, returns whether egg was added and its id"""
        egg_id = sha256(name.encode() + author_id.encode() + SALT.encode()).hexdigest()
        try:
            self.conn.execute(
                self.__EGG_INSERT_QUERY__,
                (egg_id, name, hint, author_id, author, author_avatar, max_redeems, texture, textureSize),
            )
            self.conn.commit()
        except sqlite.IntegrityError:
            return False, egg_id
        return True, egg_id

    def get_egg(self, egg_id: str) -> Egg:
        try:
            ret = self.conn.execute(self.__GET_EGGS_QUERY__, (egg_id,)).fetchone()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        return self._row_to_egg(ret)

    def update_egg(
        self,
        egg_id: str,
        name: str,
        hint: str,
        author_id: str,
        author: str,
        author_avatar: str,
        max_redeems: int,
        texture: str,
        textureSize: int,
    ) -> bool:
        """Updates an existing egg, returns whether it was updated"""
        try:
            before = self.conn.total_changes
            self.conn.execute(
                self.__EGG_UPDATE_QUERY__,
                (name, hint, author, author_avatar, max_redeems, texture, textureSize, egg_id, author_id),
            )
            self.conn.commit()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        return self.conn.total_changes > before
    def dislike_egg(self, user_id: str, egg_id: str) -> None:
        try:
            self.conn.execute(
                self.__DISLIKE_EGG_QUERY__, {"id": egg_id, "user_id": user_id}
            )
            self.conn.commit()
        except Exception as e:
            raise DBError(e) from e

    def like_egg(self, user_id: str, egg_id: str) -> None:
        try:
            self.conn.execute(
                self.__LIKE_EGG_QUERY__, {"id": egg_id, "user_id": user_id}
            )
            self.conn.commit()
        except Exception as e:
            raise DBError(e) from e

    def redeem_egg(self, user_id: str | int, egg_id: str) -> bool:
        uid = str(user_id)
        try:
            before = self.conn.total_changes
            self.conn.execute(self.__REDEEM_EGG_QUERY__, {"id": egg_id, "user_id": uid})
            self.conn.commit()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        else:
            return self.conn.total_changes > before

    def delete_egg(self, egg_id: str) -> None:
        """Deletes an egg from the database"""
        try:
            self.conn.execute(self.__DELETE_EGG_QUERY__, (egg_id,))
            self.conn.commit()
        except sqlite.OperationalError as e:
            raise DBError(e) from e

    def list_eggs(self) -> list[Egg]:
        """Returns a list of all eggs in the database"""
        try:
            return [
                self._row_to_egg(row)
                for row in self.conn.execute(
                    "SELECT id, name, hint, author_id, author, author_avatar, "
                    "max_redeems, redeems, created_at, texture, textureSize FROM eyren"
                )
            ]
        except sqlite.OperationalError as e:
            raise DBError(e) from e

    def get_user_eggs(self, user_id: str) -> list[Egg]:
        """Returns all eggs redeemed by a user"""
        try:
            rows = self.conn.execute(self.__GET_USER_EGGS_QUERY__, (user_id,)).fetchall()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        return [self._row_to_egg(row) for row in rows]
 
    def get_created_eggs(self, user_id: str) -> list[Egg]:
        """Returns all eggs created by a user"""
        try:
            rows = self.conn.execute(self.__GET_CREATED_EGGS_QUERY__, (user_id,)).fetchall()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        return [self._row_to_egg(row) for row in rows]

if __name__ == "__main__":
    db = DB("db.db")
    with db as db:
        db.add_egg("test", "test", "000000000000000000", "testuser", "", "test", -1, 0)

