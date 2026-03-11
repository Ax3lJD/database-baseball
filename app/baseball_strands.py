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
        # Only include queries that work with our available tables (people, batting, teams)
        themes = {
            "Home Run Leaders": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_HR) >= 300
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                ORDER BY RANDOM()
                LIMIT :limit
            """,

            "Batting Champions": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                WHERE b.b_AB >= 502
                AND (CAST(b.b_H AS FLOAT) / NULLIF(b.b_AB, 0)) >= 0.350
                AND LENGTH(p.nameLast) BETWEEN 4 AND 8
                GROUP BY p.playerID, p.nameLast
                ORDER BY RANDOM()
                LIMIT :limit
            """
        }

        if theme in themes:
            num_words = random.randint(self.min_words, self.max_words)
            words = []
            try:
                query = text(themes[theme])
                results = session_db.execute(query, {"limit": num_words}).fetchall()
                words = [row[0].upper() for row in results if row[0] and row[0].isalpha()]
            except Exception:
                try:
                    session_db.rollback()
                except Exception:
                    pass

            # If not enough words found, add some generic baseball terms
            if len(words) < self.min_words:
                backup_words = ["STRIKE", "BALL", "HOME", "BASE", "PITCH", "CATCH", "SLIDE",
                                "HOMER", "MOUND", "STEAL", "BUNT", "DUGOUT", "PLATE", "SWING"]
                random.shuffle(backup_words)
                words.extend(backup_words[:self.min_words - len(words)])

            return words[:num_words]

        return []

    def get_daily_puzzle(self, session_db):
        """Generate a daily puzzle using database"""
        today = date.today()
        random.seed(today.strftime("%Y%m%d"))

        # Select theme (only themes with working DB queries or good fallback)
        themes = [
            "Home Run Leaders",
            "Batting Champions",
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

    def get_hint(self, puzzle, found_words, hint_level=1):
        """Generate hints based on difficulty level"""
        remaining_words = [word for word in puzzle['words'] if word not in found_words]

        if not remaining_words:
            return None

        # Choose a word to hint about
        hint_word = random.choice(remaining_words)

        # Find the word's position in the grid
        word_position = None
        for placed_word in puzzle['placed_words']:
            if placed_word['word'] == hint_word:
                word_position = placed_word
                break

        if hint_level == 1:
            # Basic hint: word length and first letter
            return {
                'type': 'basic',
                'message': f"Look for a {len(hint_word)}-letter word starting with '{hint_word[0]}'"
            }

        elif hint_level == 2:
            # Medium hint: first two letters and general direction
            if word_position:
                direction = self._get_direction_description(word_position['direction'])
                return {
                    'type': 'medium',
                    'message': f"Look for '{hint_word[:2]}...' going {direction}"
                }
            else:
                return {
                    'type': 'medium',
                    'message': f"Look for a word starting with '{hint_word[:2]}'"
                }

        elif hint_level == 3:
            # Advanced hint: highlight starting area
            if word_position:
                row, col = word_position['start']
                return {
                    'type': 'advanced',
                    'message': f"Check around row {row + 1}, column {col + 1} for '{hint_word[:3]}...'"
                }
            else:
                return {
                    'type': 'advanced',
                    'message': f"Look for '{hint_word[:3]}...' (starts with these letters)"
                }

        elif hint_level >= 4:
            # Ultimate hint: show the full word
            return {
                'type': 'reveal',
                'message': f"Find the word: {hint_word}",
                'word': hint_word
            }

    def _get_direction_description(self, direction):
        """Convert direction tuple to human-readable description"""
        if direction == (0, 1):
            return "horizontally (left to right)"
        elif direction == (1, 0):
            return "vertically (top to bottom)"
        elif direction == (1, 1):
            return "diagonally (down-right)"
        elif direction == (-1, 1):
            return "diagonally (up-right)"
        else:
            return "in an unknown direction"

    def highlight_hint_cells(self, puzzle, hint_word):
        """Get cells to highlight for a specific word"""
        highlighted_cells = []

        for placed_word in puzzle['placed_words']:
            if placed_word['word'] == hint_word:
                start_row, start_col = placed_word['start']
                direction = placed_word['direction']

                # Highlight the first 3 letters
                for i in range(min(3, len(hint_word))):
                    row = start_row + i * direction[0]
                    col = start_col + i * direction[1]
                    highlighted_cells.append((row, col))

                break

        return highlighted_cells