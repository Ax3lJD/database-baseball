import random
from datetime import date
import string
from sqlalchemy import text


class BaseballStrands:
    def __init__(self):
        self.grid_size = 10
        self.min_words = 6
        self.max_words = 8

    def get_themed_words(self, session_db, theme):
        """Get words from database based on theme"""
        themes = {
            "Hall of Fame Players": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN halloffame h ON p.playerID = h.playerID
                WHERE h.inducted = 'Y'
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                ORDER BY RAND()
                LIMIT :limit
            """,

            "Team Cities": """
                SELECT DISTINCT 
                    CASE 
                        WHEN team_name LIKE '% %' THEN SUBSTRING_INDEX(team_name, ' ', 1)
                        ELSE team_name
                    END as city
                FROM teams
                WHERE yearID >= 1990
                AND team_name IS NOT NULL
                HAVING LENGTH(city) BETWEEN 4 AND 8
                AND city NOT IN ('of', 'the', 'and')
                ORDER BY RAND()
                LIMIT :limit
            """,

            "MVP Winners": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN awards a ON p.playerID = a.playerID
                WHERE a.awardID = 'Most Valuable Player'
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                ORDER BY RAND()
                LIMIT :limit
            """,

            "Home Run Leaders": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_HR) >= 300
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                ORDER BY RAND()
                LIMIT :limit
            """,

            "Cy Young Winners": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN awards a ON p.playerID = a.playerID
                WHERE a.awardID = 'Cy Young Award'
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                ORDER BY RAND()
                LIMIT :limit
            """,

            "Stadium Names": """
                SELECT DISTINCT 
                    CASE 
                        WHEN park_name LIKE '% Park' THEN SUBSTRING_INDEX(park_name, ' Park', 1)
                        WHEN park_name LIKE '% Field' THEN SUBSTRING_INDEX(park_name, ' Field', 1)
                        WHEN park_name LIKE '% Stadium' THEN SUBSTRING_INDEX(park_name, ' Stadium', 1)
                        ELSE park_name
                    END as stadium_name
                FROM parks
                WHERE park_name IS NOT NULL
                HAVING LENGTH(stadium_name) BETWEEN 4 AND 8
                AND stadium_name NOT LIKE '%/%'
                ORDER BY RAND()
                LIMIT :limit
            """,

            "Batting Champions": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                WHERE b.b_AB >= 502
                AND (b.b_H / NULLIF(b.b_AB, 0)) >= 0.350
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                GROUP BY p.playerID, p.nameLast
                ORDER BY RAND()
                LIMIT :limit
            """
        }

        if theme in themes:
            num_words = random.randint(self.min_words, self.max_words)
            query = text(themes[theme])
            results = session_db.execute(query, {"limit": num_words}).fetchall()
            words = [row[0].upper() for row in results if row[0] and row[0].isalpha()]

            # If not enough words found, add some generic baseball terms
            if len(words) < self.min_words:
                backup_words = ["STRIKE", "BALL", "HOME", "BASE", "PITCH", "CATCH", "SLIDE"]
                random.shuffle(backup_words)
                words.extend(backup_words[:self.min_words - len(words)])

            return words[:num_words]

        return []

    def get_daily_puzzle(self, session_db):
        """Generate a daily puzzle using database"""
        today = date.today()
        random.seed(today.strftime("%Y%m%d"))

        # Select theme
        themes = [
            "Hall of Fame Players",
            "Team Cities",
            "MVP Winners",
            "Home Run Leaders",
            "Cy Young Winners",
            "Stadium Names",
            "Batting Champions"
        ]
        theme = random.choice(themes)

        # Get words from database
        words = self.get_themed_words(session_db, theme)

        # Create grid
        grid = self._create_empty_grid()
        placed_words = []

        # Place words in grid
        for word in words:
            placed = self._place_word(grid, word)
            if placed:
                placed_words.append(placed)

        # Fill remaining spaces
        self._fill_grid(grid)

        return {
            "theme": theme,
            "grid": grid,
            "words": words,
            "placed_words": placed_words,
            "date": today.strftime("%Y-%m-%d")
        }

    def _create_empty_grid(self):
        return [['' for _ in range(self.grid_size)] for _ in range(self.grid_size)]

    def _place_word(self, grid, word):
        directions = [(0, 1), (1, 0), (1, 1), (-1, 1)]  # right, down, diagonal-right, diagonal-left

        for _ in range(100):  # Try 100 times to place the word
            direction = random.choice(directions)
            row = random.randint(0, self.grid_size - 1)
            col = random.randint(0, self.grid_size - 1)

            if self._can_place_word(grid, word, row, col, direction):
                for i, letter in enumerate(word):
                    new_row = row + i * direction[0]
                    new_col = col + i * direction[1]
                    grid[new_row][new_col] = letter

                return {
                    "word": word,
                    "start": (row, col),
                    "end": (row + (len(word) - 1) * direction[0],
                            col + (len(word) - 1) * direction[1]),
                    "direction": direction
                }

        return None

    def _can_place_word(self, grid, word, row, col, direction):
        for i, letter in enumerate(word):
            new_row = row + i * direction[0]
            new_col = col + i * direction[1]

            if (new_row < 0 or new_row >= self.grid_size or
                    new_col < 0 or new_col >= self.grid_size):
                return False

            if grid[new_row][new_col] != '' and grid[new_row][new_col] != letter:
                return False

        return True

    def _fill_grid(self, grid):
        letters = string.ascii_uppercase
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == '':
                    grid[i][j] = random.choice(letters)

