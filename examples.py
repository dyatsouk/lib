"""Example statistical queries over simulated mafia games."""

from mafia.history import GameHistoryDB


def main() -> None:
    db = GameHistoryDB("games.db")
    cur = db.conn.cursor()

    # 1) Percentage of games where sheriff was killed on first night that were won by civilians
    q1 = (
        """
        WITH sheriff AS (
            SELECT g.id, p.key AS pid
            FROM games g, json_each(g.history, '$.players') AS p
            WHERE p.value = 'SHERIFF'
        )
        SELECT 100.0 * SUM(CASE WHEN g.winner = 'CIVILIAN' THEN 1 ELSE 0 END) / COUNT(*)
        FROM games g
        JOIN sheriff s ON g.id = s.id
        WHERE json_extract(g.history, '$.rounds[0].night.kill') = s.pid
        """
    )
    cur.execute(q1)
    pct = cur.fetchone()[0]
    print(f"Civilian win % when sheriff dies night1: {pct or 0:.2f}")

    # 2) Distribution of rounds that the game lasted given mafia won
    q2 = (
        """
        SELECT json_array_length(json_extract(history, '$.rounds')) AS rounds, COUNT(*)
        FROM games
        WHERE winner = 'MAFIA'
        GROUP BY rounds
        ORDER BY rounds
        """
    )
    cur.execute(q2)
    print("Round distribution for mafia wins:", cur.fetchall())

    # 3) Civilian win rate when nobody is eliminated on first day voting
    q3 = (
        """
        SELECT 100.0 * SUM(CASE WHEN winner = 'CIVILIAN' THEN 1 ELSE 0 END) / COUNT(*)
        FROM games
        WHERE json_extract(history, '$.rounds[0].day.eliminated') IS NULL
        """
    )
    cur.execute(q3)
    pct = cur.fetchone()[0]
    print(f"Civilian win % with no day1 elimination: {pct or 0:.2f}")

    # 4) Total nominations across all games
    q4 = (
        """
        SELECT SUM(noms) FROM (
            SELECT (
                SELECT COUNT(*)
                FROM json_each(history, '$.rounds') AS r
                JOIN json_each(json_extract(history, '$.rounds[' || r.key || '].day.speeches')) AS s
                WHERE json_extract(s.value, '$.action.nomination') IS NOT NULL
            ) AS noms
            FROM games
        )
        """
    )
    cur.execute(q4)
    total_noms = cur.fetchone()[0]
    print(f"Total nominations across all games: {total_noms or 0}")

    db.close()


if __name__ == "__main__":
    main()
