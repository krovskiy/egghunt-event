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
    reward: str
    salted_hash: str


class DB:
    """sqlite3 database management class"""

    __INIT_SQL_QUERY__ = """
                         CREATE TABLE IF NOT EXISTS eyren
                         (
                             id             TEXT PRIMARY KEY,
                             name           TEXT    NOT NULL,
                             hint           TEXT    NOT NULL,
                             author_id      TEXT    NOT NULL,
                             author         TEXT    NOT NULL,
                             author_avatar  TEXT    NOT NULL DEFAULT '',
                             max_redeems    INTEGER NOT NULL DEFAULT 1,
                             redeems        INTEGER NOT NULL DEFAULT 0,
                             created_at     TEXT             DEFAULT CURRENT_TIMESTAMP,
                             redeemed_users TEXT DEFAULT '',
                             texture        TEXT,
                             textureSize    INTEGER NOT NULL DEFAULT 0,
                             liked_users    TEXT,
                             disliked_users TEXT,
                             reward         TEXT    NOT NULL DEFAULT '',
                             salted_hash    TEXT    NOT NULL DEFAULT ''
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
                            textureSize,
                            reward,
                            salted_hash)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                           """

    __EGG_UPDATE_QUERY__ = """
                           UPDATE eyren
                           SET name          = ?,
                               hint          = ?,
                               author        = ?,
                               author_avatar = ?,
                               max_redeems   = ?,
                               texture       = ?,
                               textureSize   = ?,
                               reward        = ?
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
                                textureSize,
                                reward,
                                salted_hash
                         FROM eyren
                         WHERE id = (?);
                         """

    __GET_EGG_BY_HASH_QUERY__ = """
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
                                       textureSize,
                                       reward,
                                       salted_hash
                                FROM eyren
                                WHERE salted_hash = (?);
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
                                textureSize,
                                reward,
                                salted_hash
                              FROM eyren
                              WHERE ',' || redeemed_users || ',' LIKE '%,' || (?) || ',%';
                              """

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
                                    textureSize,
                                    reward,
                                    salted_hash
                                FROM eyren
                                WHERE author_id = (?);
                                """

    __LEADERBOARD_SOURCE_QUERY__ = """
                                   SELECT author_id,
                                       author,
                                       author_avatar,
                                       liked_users,
                                       redeemed_users
                                   FROM eyren;
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

    def _migrate(self, conn: sqlite.Connection) -> None:
        """Add new columns to existing databases that predate this schema."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(eyren)")}
        migrations = [
            ("author_id",     "ALTER TABLE eyren ADD COLUMN author_id     TEXT NOT NULL DEFAULT ''"),
            ("author_avatar", "ALTER TABLE eyren ADD COLUMN author_avatar TEXT NOT NULL DEFAULT ''"),
            ("reward",        "ALTER TABLE eyren ADD COLUMN reward        TEXT NOT NULL DEFAULT ''"),
            ("salted_hash",   "ALTER TABLE eyren ADD COLUMN salted_hash   TEXT NOT NULL DEFAULT ''"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(sql)

        # Backfill salted_hash for existing rows that predate this column.
        try:
            rows = conn.execute(
                "SELECT id FROM eyren WHERE salted_hash IS NULL OR salted_hash = ''"
            ).fetchall()
        except sqlite.Error:
            rows = []

        for (egg_id,) in rows:
            salted_hash = self._make_salted_hash(egg_id)
            conn.execute(
                "UPDATE eyren SET salted_hash = ? WHERE id = ?",
                (salted_hash, egg_id),
            )

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
            reward=row[11] or "",
            salted_hash=row[12] or "",
        )

    @staticmethod
    def _make_salted_hash(egg_id: str) -> str:
        """Secondary hash for QR codes and public URLs. Distinct from the primary egg_id."""
        return sha256((egg_id + SALT + "qr").encode()).hexdigest()

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
        reward: str = "",
    ) -> tuple[bool, str]:
        """Adds an egg to the database, returns whether egg was added and its id"""
        egg_id = sha256(name.encode() + author_id.encode() + SALT.encode()).hexdigest()
        salted_hash = self._make_salted_hash(egg_id)
        try:
            self.conn.execute(
                self.__EGG_INSERT_QUERY__,
                (egg_id, name, hint, author_id, author, author_avatar, max_redeems, texture, textureSize, reward, salted_hash),
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

    def get_egg_by_hash(self, salted_hash: str) -> Egg:
        """Fetch an egg by its public salted_hash (used for QR code URLs)."""
        try:
            ret = self.conn.execute(
                self.__GET_EGG_BY_HASH_QUERY__, (salted_hash,)
            ).fetchone()
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
        reward: str = "",
    ) -> bool:
        """Updates an existing egg, returns whether it was updated"""
        try:
            before = self.conn.total_changes
            self.conn.execute(
                self.__EGG_UPDATE_QUERY__,
                (name, hint, author, author_avatar, max_redeems, texture, textureSize, reward, egg_id, author_id),
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
                    "max_redeems, redeems, created_at, texture, textureSize, reward, salted_hash FROM eyren"
                )
            ]
        except sqlite.OperationalError as e:
            raise DBError(e) from e

    def list_eggs_by_feedback(self, limit: int | None = None, offset: int = 0) -> list[dict]:
        """Returns eggs sorted by like/dislike ratio and redeems, with counts."""
        query = """
            SELECT
                id,
                name,
                hint,
                author_id,
                author,
                author_avatar,
                max_redeems,
                redeems,
                created_at,
                texture,
                textureSize,
                reward,
                salted_hash,
                CASE
                    WHEN liked_users IS NULL OR liked_users = '' THEN 0
                    ELSE (length(liked_users) - length(replace(liked_users, ',', '')) + 1)
                END AS like_count,
                CASE
                    WHEN disliked_users IS NULL OR disliked_users = '' THEN 0
                    ELSE (length(disliked_users) - length(replace(disliked_users, ',', '')) + 1)
                END AS dislike_count
            FROM eyren
            ORDER BY
                CASE
                    WHEN (
                        CASE WHEN liked_users IS NULL OR liked_users = '' THEN 0
                             ELSE (length(liked_users) - length(replace(liked_users, ',', '')) + 1)
                        END
                        +
                        CASE WHEN disliked_users IS NULL OR disliked_users = '' THEN 0
                             ELSE (length(disliked_users) - length(replace(disliked_users, ',', '')) + 1)
                        END
                    ) = 0 THEN 0
                    ELSE 1.0 *
                        CASE WHEN liked_users IS NULL OR liked_users = '' THEN 0
                             ELSE (length(liked_users) - length(replace(liked_users, ',', '')) + 1)
                        END /
                        (
                            CASE WHEN liked_users IS NULL OR liked_users = '' THEN 0
                                 ELSE (length(liked_users) - length(replace(liked_users, ',', '')) + 1)
                            END
                            +
                            CASE WHEN disliked_users IS NULL OR disliked_users = '' THEN 0
                                 ELSE (length(disliked_users) - length(replace(disliked_users, ',', '')) + 1)
                            END
                        )
                END DESC,
                redeems DESC,
                created_at DESC,
                id ASC
        """
        params: tuple = ()
        if limit is not None:
            query = f"{query} LIMIT ? OFFSET ?"
            params = (limit, offset)
        try:
            rows = self.conn.execute(query, params).fetchall()
        except sqlite.OperationalError as e:
            raise DBError(e) from e

        results = []
        for row in rows:
            egg = self._row_to_egg(row[:13])
            results.append({
                "egg": egg,
                "like_count": row[13],
                "dislike_count": row[14],
            })
        return results

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

    def get_leaderboard_source(self) -> list[tuple]:
        """Returns minimal data needed to build leaderboards."""
        try:
            rows = self.conn.execute(self.__LEADERBOARD_SOURCE_QUERY__).fetchall()
        except sqlite.OperationalError as e:
            raise DBError(e) from e
        return rows
