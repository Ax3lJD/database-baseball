import random
from datetime import date, datetime
from sqlalchemy import text


class BaseballWordle:
    def __init__(self):
        self.max_attempts = 6
        self.word_length = 5

        # Hall of Famers and star players with 5-letter names
        self.featured_players = [
            'AARON',  # Hank Aaron
            'BONDS',  # Barry Bonds
            'JETER',  # Derek Jeter
            'TROUT',  # Mike Trout
            'BENCH',  # Johnny Bench
            'BERRA',  # Yogi Berra
            'BANKS',  # Ernie Banks
            'SPAHN',  # Warren Spahn
            'GWYNN',  # Tony Gwynn
            'ROLEN',  # Scott Rolen
        ]

        # Common names for easier difficulty
        self.common_names = [
            'SMITH', 'JONES', 'BROWN', 'DAVIS', 'MOORE',
            'WHITE', 'YOUNG', 'CLARK', 'PEREZ', 'KELLY'
        ]

        # Medium difficulty names
        self.medium_names = [
            'BAKER', 'LOPEZ', 'SCOTT', 'GREEN', 'LEWIS',
            'BURNS', 'BURKE', 'EVANS', 'ALLEN', 'ADAMS'
        ]

    def get_word_by_difficulty(self, session_db, difficulty='medium'):
        """Get a 5-letter baseball player last name based on difficulty"""
        if difficulty == 'easy':
            pool = self.common_names
        elif difficulty == 'medium':
            # Mix of common and less common names
            pool = self.medium_names + random.sample(self.common_names, 5)
        elif difficulty == 'hard':
            # Featured players or rare names from database
            if random.random() < 0.6:  # 60% chance for featured player
                pool = self.featured_players
            else:
                try:
                    query = text("""
                        SELECT DISTINCT p.nameLast
                        FROM people p
                        JOIN batting b ON p.playerID = b.playerID
                        WHERE LENGTH(p.nameLast) = 5
                        AND p.nameLast ~ '^[A-Za-z]+$'
                        GROUP BY p.playerID, p.nameLast
                        HAVING SUM(b.b_AB) > 500
                        ORDER BY RANDOM()
                        LIMIT 20
                    """)
                    results = session_db.execute(query).fetchall()
                    pool = [row[0].upper() for row in results]
                except Exception:
                    try:
                        session_db.rollback()
                    except Exception:
                        pass
                    pool = []
        else:  # random
            try:
                query = text("""
                    SELECT DISTINCT nameLast
                    FROM people
                    WHERE LENGTH(nameLast) = 5
                    AND nameLast ~ '^[A-Za-z]+$'
                    ORDER BY RANDOM()
                    LIMIT 50
                """)
                results = session_db.execute(query).fetchall()
                pool = [row[0].upper() for row in results]
            except Exception:
                try:
                    session_db.rollback()
                except Exception:
                    pass
                pool = []

        if not pool:
            pool = self.common_names  # Fallback

        return random.choice(pool)

    def get_player_hint(self, session_db, word, attempt_number):
        """Get progressively more helpful hints based on attempt number"""
        try:
            query = text("""
                SELECT p.nameFirst, p.nameLast,
                       MIN(b.yearId) as first_year, MAX(b.yearId) as last_year,
                       COUNT(DISTINCT b.yearId) as num_seasons,
                       SUM(b.b_AB) as total_ab, SUM(b.b_HR) as total_hr,
                       SUM(b.b_RBI) as total_rbi
                FROM people p
                LEFT JOIN batting b ON p.playerID = b.playerID
                WHERE UPPER(p.nameLast) = :word
                GROUP BY p.playerID, p.nameFirst, p.nameLast
                ORDER BY total_ab DESC NULLS LAST
                LIMIT 1
            """)

            result = session_db.execute(query, {"word": word}).fetchone()
        except Exception:
            try:
                session_db.rollback()
            except Exception:
                pass
            result = None

        if not result:
            return self._get_generic_hint(attempt_number)

        first_name, last_name, first_year, last_year, num_seasons, ab, hrs, rbis = result

        # Progressive hints based on attempt number
        if attempt_number == 3:
            if first_year and last_year:
                decade = f"{(first_year // 10) * 10}s"
                if last_year > 2010:
                    era = "modern era"
                elif last_year > 1990:
                    era = "recent era"
                elif last_year > 1970:
                    era = "modern era"
                else:
                    era = "classic era"
                return f"This {era} player was active in the {decade}"
            else:
                return "This player's name appears in baseball records"

        elif attempt_number == 4:
            if hrs and ab and hrs > 0:
                hr_rate = hrs / max(ab, 1) * 600  # approx HRs per 600 AB
                if hr_rate > 30:
                    power_desc = "power hitter"
                elif hr_rate > 15:
                    power_desc = "solid hitter"
                else:
                    power_desc = "contact hitter"
                return f"This {power_desc} played {num_seasons or '?'} seasons"
            else:
                return f"This player played {num_seasons or '?'} seasons"

        elif attempt_number == 5:
            first_letter = first_name[0] if first_name else "?"
            if first_year and last_year:
                years_played = last_year - first_year + 1
                return f"First name starts with '{first_letter}', played {years_played} seasons"
            else:
                return f"First name starts with '{first_letter}'"

        else:
            return self._get_generic_hint(attempt_number)

    def _get_generic_hint(self, attempt_number):
        """Generic hints when player data isn't available"""
        if attempt_number == 3:
            return "This is a 5-letter baseball player's last name"
        elif attempt_number == 4:
            return "Think of famous baseball players with 5-letter names"
        elif attempt_number == 5:
            return "This player has appeared in MLB games"
        else:
            return "Keep guessing!"

    def check_guess(self, guess, target):
        """Return feedback for each letter: correct, present, or absent"""
        guess = guess.upper()
        target = target.upper()

        result = []
        target_chars = list(target)

        # First pass: mark correct positions
        for i, char in enumerate(guess):
            if i < len(target) and char == target[i]:
                result.append('correct')
                target_chars[i] = None  # Mark as used
            else:
                result.append(None)

        # Second pass: mark present but wrong position
        for i, char in enumerate(guess):
            if result[i] is None:
                if char in target_chars:
                    result[i] = 'present'
                    target_chars[target_chars.index(char)] = None
                else:
                    result[i] = 'absent'

        return result
