# app/baseball_crossword.py
import random
from datetime import date, datetime
from sqlalchemy import text
import json


class BaseballCrossword:
    def __init__(self):
        self.grid_size = 7
        self.difficulty_levels = ['easy', 'medium', 'hard']

        # Hardcoded word pools for fallback puzzles
        self._player_words = [
            ("RUTH", "714 career home runs, the Sultan of Swat"),
            ("MAYS", "Say Hey Kid, 660 career home runs"),
            ("AARON", "All-time HR king for 33 years (755)"),
            ("BONDS", "All-time HR leader with 762"),
            ("JETER", "Yankees captain, 3,465 career hits"),
            ("TROUT", "Angels star, multiple MVP winner"),
            ("COBB", "Lifetime .366 batting average"),
            ("ROSE", "All-time hits leader with 4,256"),
            ("BANKS", "Mr. Cub, 512 career home runs"),
            ("BENCH", "Reds catcher, 2x MVP winner"),
            ("GWYNN", "8x NL batting champion"),
            ("PUJOLS", "700+ HR club member"),
            ("SOSA", "66 HR in 1998 season"),
            ("FOXX", "Triple Crown winner, 534 HRs"),
            ("SMITH", "Common baseball surname"),
            ("JONES", "Common baseball surname"),
            ("CLARK", "Will Clark, Giants first baseman"),
            ("YOUNG", "Cy Young, 511 career wins"),
        ]

        self._stat_words = [
            ("ERA", "Earned Run Average"),
            ("RBI", "Runs Batted In"),
            ("OPS", "On-base Plus Slugging"),
            ("SAVE", "Pitching statistic for closers"),
            ("BALK", "Illegal pitching motion"),
            ("SLUG", "Slugging percentage"),
            ("WHIP", "Walks plus Hits per Inning Pitched"),
            ("CYCLE", "Single, double, triple, homer in one game"),
            ("STEAL", "Taking a base while pitcher delivers"),
            ("HOMER", "A home run"),
            ("BUNT", "Soft tap to advance runners"),
            ("SWING", "Bat motion at a pitch"),
        ]

        self._team_words = [
            ("CUBS", "Chicago NL team, Wrigley Field"),
            ("REDS", "Cincinnati team, Big Red Machine"),
            ("METS", "New York NL team, Shea Stadium"),
            ("RAYS", "Tampa Bay team, Tropicana Field"),
            ("TWINS", "Minnesota team, Target Field"),
            ("PADRES", "San Diego team, Petco Park"),
            ("BRAVES", "Atlanta team, moved from Milwaukee"),
            ("GIANTS", "San Francisco team, Oracle Park"),
        ]

    def _get_fallback_puzzle(self, puzzle_type='player'):
        """Generate a puzzle from hardcoded data"""
        if puzzle_type == 'player':
            words = list(self._player_words)
            theme = 'Baseball Legends'
        elif puzzle_type == 'team':
            words = list(self._team_words)
            theme = 'Baseball Franchises'
        else:
            words = list(self._stat_words)
            theme = 'Baseball Statistics & Records'

        random.shuffle(words)

        # Build simple word objects for the grid builder
        word_entries = []
        for word_text, clue in words:
            if 3 <= len(word_text) <= self.grid_size:
                word_entries.append((word_text, clue))

        # Place words into a grid
        grid, word_positions = self._create_simple_grid(word_entries)

        return {
            'theme': theme,
            'grid': grid,
            'across_clues': word_positions.get('across_clues', {}),
            'down_clues': word_positions.get('down_clues', {}),
            'difficulty': 'medium',
            'word_positions': {'across': word_positions.get('across', {}),
                               'down': word_positions.get('down', {})}
        }

    def _create_simple_grid(self, word_entries):
        """Create a simple crossword grid from word entries"""
        grid = [[' ' for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        placed = []
        across_clues = {}
        down_clues = {}
        across_positions = {}
        down_positions = {}
        used_positions = set()
        clue_num = 1

        # Sort by length descending
        word_entries.sort(key=lambda x: -len(x[0]))

        for word_text, clue in word_entries:
            if len(placed) >= 8:
                break

            if not placed:
                # Place first word horizontally in middle
                row = self.grid_size // 2
                col = max(0, (self.grid_size - len(word_text)) // 2)
                if col + len(word_text) <= self.grid_size:
                    for i, letter in enumerate(word_text):
                        grid[row][col + i] = letter
                        used_positions.add((row, col + i))
                    across_clues[str(clue_num)] = {
                        'clue': clue, 'answer': word_text, 'row': row, 'col': col
                    }
                    across_positions[str(clue_num)] = {
                        'word': word_text, 'row': row, 'col': col, 'answer': word_text
                    }
                    placed.append((word_text, 'across', row, col))
                    clue_num += 1
                continue

            # Try to intersect with existing words
            did_place = False
            for _ in range(50):
                # Pick a random placed word to intersect with
                ref_word, ref_dir, ref_row, ref_col = random.choice(placed)

                # Find common letters
                for wi, wc in enumerate(word_text):
                    for ri, rc in enumerate(ref_word):
                        if wc == rc:
                            if ref_dir == 'across':
                                # Place new word vertically
                                new_col = ref_col + ri
                                new_row = ref_row - wi
                                if self._try_place_vertical(grid, word_text, new_row, new_col, used_positions):
                                    for i, letter in enumerate(word_text):
                                        grid[new_row + i][new_col] = letter
                                        used_positions.add((new_row + i, new_col))
                                    down_clues[str(clue_num)] = {
                                        'clue': clue, 'answer': word_text,
                                        'row': new_row, 'col': new_col
                                    }
                                    down_positions[str(clue_num)] = {
                                        'word': word_text, 'row': new_row, 'col': new_col,
                                        'answer': word_text
                                    }
                                    placed.append((word_text, 'down', new_row, new_col))
                                    clue_num += 1
                                    did_place = True
                                    break
                            else:
                                # Place new word horizontally
                                new_row = ref_row + ri
                                new_col = ref_col - wi
                                if self._try_place_horizontal(grid, word_text, new_row, new_col, used_positions):
                                    for i, letter in enumerate(word_text):
                                        grid[new_row][new_col + i] = letter
                                        used_positions.add((new_row, new_col + i))
                                    across_clues[str(clue_num)] = {
                                        'clue': clue, 'answer': word_text,
                                        'row': new_row, 'col': new_col
                                    }
                                    across_positions[str(clue_num)] = {
                                        'word': word_text, 'row': new_row, 'col': new_col,
                                        'answer': word_text
                                    }
                                    placed.append((word_text, 'across', new_row, new_col))
                                    clue_num += 1
                                    did_place = True
                                    break
                    if did_place:
                        break
                if did_place:
                    break

        return grid, {
            'across': across_positions, 'down': down_positions,
            'across_clues': across_clues, 'down_clues': down_clues
        }

    def _try_place_horizontal(self, grid, word, row, col, used_positions):
        """Check if word can be placed horizontally"""
        if row < 0 or row >= self.grid_size:
            return False
        if col < 0 or col + len(word) > self.grid_size:
            return False
        for i, letter in enumerate(word):
            c = col + i
            if (row, c) in used_positions:
                if grid[row][c] != letter:
                    return False
            else:
                # Check above/below for adjacency issues
                if row > 0 and grid[row - 1][c] != ' ' and (row - 1, c) not in used_positions:
                    return False
                if row < self.grid_size - 1 and grid[row + 1][c] != ' ':
                    return False
        # Check ends
        if col > 0 and grid[row][col - 1] != ' ':
            return False
        if col + len(word) < self.grid_size and grid[row][col + len(word)] != ' ':
            return False
        return True

    def _try_place_vertical(self, grid, word, row, col, used_positions):
        """Check if word can be placed vertically"""
        if col < 0 or col >= self.grid_size:
            return False
        if row < 0 or row + len(word) > self.grid_size:
            return False
        for i, letter in enumerate(word):
            r = row + i
            if (r, col) in used_positions:
                if grid[r][col] != letter:
                    return False
            else:
                if col > 0 and grid[r][col - 1] != ' ' and (r, col - 1) not in used_positions:
                    return False
                if col < self.grid_size - 1 and grid[r][col + 1] != ' ':
                    return False
        # Check ends
        if row > 0 and grid[row - 1][col] != ' ':
            return False
        if row + len(word) < self.grid_size and grid[row + len(word)][col] != ' ':
            return False
        return True

    def generate_player_based_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using player names"""
        return self._get_fallback_puzzle('player')

    def generate_team_based_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using team names"""
        return self._get_fallback_puzzle('team')

    def generate_statistical_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using baseball statistics"""
        return self._get_fallback_puzzle('stat')

    def get_daily_puzzle(self, session_db):
        """Get the daily crossword puzzle"""
        days_since_epoch = (date.today() - date(2024, 1, 1)).days
        random.seed(days_since_epoch)
        puzzle_type = days_since_epoch % 3

        if puzzle_type == 0:
            return self.generate_player_based_crossword(session_db)
        elif puzzle_type == 1:
            return self.generate_team_based_crossword(session_db)
        else:
            return self.generate_statistical_crossword(session_db)

    def check_solution(self, user_grid, solution_grid):
        """Check if the user's grid matches the solution"""
        if len(user_grid) != len(solution_grid):
            return False
        for i in range(len(solution_grid)):
            for j in range(len(solution_grid[i])):
                if solution_grid[i][j] != ' ':
                    if user_grid[i][j].upper() != solution_grid[i][j]:
                        return False
        return True

    def check_word(self, user_grid, clue_info, direction):
        """Check if a specific word is correct"""
        row = clue_info['row']
        col = clue_info['col']
        answer = clue_info['answer']

        if direction == 'across':
            for i, letter in enumerate(answer):
                if col + i >= len(user_grid[0]) or user_grid[row][col + i].upper() != letter:
                    return False
        else:
            for i, letter in enumerate(answer):
                if row + i >= len(user_grid) or user_grid[row + i][col].upper() != letter:
                    return False
        return True

    def get_hint(self, session_db, puzzle, user_grid, hint_level):
        """Provide progressive hints"""
        empty_cells = []
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if puzzle['grid'][i][j] != ' ' and user_grid[i][j] == '':
                    empty_cells.append((i, j))

        if not empty_cells:
            return None

        if hint_level <= 2:
            # Reveal a random letter
            if empty_cells:
                row, col = random.choice(empty_cells)
                return {
                    'type': 'reveal_letter',
                    'row': row,
                    'col': col,
                    'letter': puzzle['grid'][row][col]
                }

        elif hint_level >= 3:
            # Reveal a complete word
            incomplete_words = []
            for direction in ['across', 'down']:
                clues_key = f'{direction}_clues'
                if clues_key in puzzle:
                    for num, clue_info in puzzle[clues_key].items():
                        if not self.check_word(user_grid, clue_info, direction):
                            if num not in puzzle.get('completed_words', {}).get(direction, []):
                                incomplete_words.append((direction, num, clue_info))

            if incomplete_words:
                direction, num, clue_info = random.choice(incomplete_words)
                return {
                    'type': 'reveal_word',
                    'direction': direction,
                    'number': num,
                    'word': clue_info['answer'],
                    'row': clue_info['row'],
                    'col': clue_info['col']
                }

        return None
