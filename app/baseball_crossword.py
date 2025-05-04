# app/baseball_crossword.py
import random
from datetime import date, datetime
from sqlalchemy import text
import json


class BaseballCrossword:
    def __init__(self):
        self.grid_size = 7  # Larger grid for more complex puzzles
        self.difficulty_levels = ['easy', 'medium', 'hard']

    def generate_player_based_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using player names with complex database queries"""

        # Use a CTE with window functions to get top players
        query = text("""
        WITH PlayerStats AS (
            SELECT 
                p.playerID,
                p.nameLast,
                p.nameFirst,
                COALESCE(b.total_HR, 0) as career_HR,
                COALESCE(pit.total_W, 0) as career_W,
                COALESCE(b.total_hits, 0) as career_hits,
                CASE 
                    WHEN p.playerID IN (SELECT playerID FROM halloffame WHERE inducted = 'Y') THEN 1
                    ELSE 0
                END as is_HOF,
                LENGTH(p.nameLast) as name_length,
                ROW_NUMBER() OVER (PARTITION BY LENGTH(p.nameLast) ORDER BY COALESCE(b.total_HR, 0) + COALESCE(pit.total_W, 0) DESC) as rank_by_length
            FROM people p
            LEFT JOIN (
                SELECT 
                    playerID, 
                    SUM(b_HR) as total_HR,
                    SUM(b_H) as total_hits,
                    COUNT(DISTINCT yearID) as seasons
                FROM batting
                GROUP BY playerID
                HAVING seasons >= 5
            ) b ON p.playerID = b.playerID
            LEFT JOIN (
                SELECT 
                    playerID, 
                    SUM(p_W) as total_W,
                    COUNT(DISTINCT yearID) as seasons
                FROM pitching
                GROUP BY playerID
                HAVING seasons >= 3
            ) pit ON p.playerID = pit.playerID
            WHERE p.nameLast REGEXP '^[A-Z]+$'
            AND LENGTH(p.nameLast) BETWEEN 4 AND 7
            AND (b.total_HR > 50 OR pit.total_W > 50)
        ),
        SelectedPlayers AS (
            SELECT *
            FROM PlayerStats
            WHERE rank_by_length <= 3
            ORDER BY RAND()
            LIMIT 10
        )
        SELECT 
            playerID,
            nameLast,
            nameFirst,
            career_HR,
            career_W,
            career_hits,
            is_HOF,
            name_length
        FROM SelectedPlayers
        """)

        players = session_db.execute(query).fetchall()

        # Generate crossword grid with intersections
        grid, word_positions = self._create_grid_with_intersections(players)

        # Generate clues using complex queries
        clues = self._generate_player_clues(session_db, word_positions)

        return {
            'theme': 'Baseball Legends',
            'grid': grid,
            'across_clues': clues['across'],
            'down_clues': clues['down'],
            'difficulty': difficulty,
            'word_positions': word_positions
        }

    def generate_team_based_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using team names and franchise data"""

        query = text("""
        WITH TeamPerformance AS (
            SELECT 
                f.franchID,
                f.franchName,
                t.teamID,
                t.team_name,
                COUNT(DISTINCT t.yearID) as years_active,
                SUM(CASE WHEN t.WSWin = 'Y' THEN 1 ELSE 0 END) as ws_wins,
                SUM(t.team_W) as total_wins,
                AVG(t.team_W) as avg_wins,
                MAX(t.team_W) as best_season_wins,
                MIN(t.yearID) as first_year,
                MAX(t.yearID) as last_year,
                LENGTH(t.team_name) as name_length
            FROM teams t
            JOIN franchises f ON t.franchID = f.franchID
            WHERE t.team_name REGEXP '^[A-Z]+$'
            AND LENGTH(t.team_name) BETWEEN 4 AND 8
            GROUP BY f.franchID, f.franchName, t.teamID, t.team_name
            HAVING years_active >= 10
        ),
        RankedTeams AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (PARTITION BY name_length ORDER BY total_wins DESC) as rank_by_length,
                DENSE_RANK() OVER (ORDER BY ws_wins DESC, total_wins DESC) as overall_rank
            FROM TeamPerformance
        )
        SELECT 
            franchID,
            franchName,
            teamID,
            team_name as word,
            ws_wins,
            total_wins,
            avg_wins,
            best_season_wins,
            first_year,
            last_year,
            name_length
        FROM RankedTeams
        WHERE rank_by_length <= 3
        ORDER BY RAND()
        LIMIT 12
        """)

        teams = session_db.execute(query).fetchall()

        grid, word_positions = self._create_grid_with_intersections(teams)
        clues = self._generate_team_clues(session_db, word_positions)

        return {
            'theme': 'Baseball Franchises',
            'grid': grid,
            'across_clues': clues['across'],
            'down_clues': clues['down'],
            'difficulty': difficulty,
            'word_positions': word_positions
        }

    def generate_statistical_crossword(self, session_db, difficulty='medium'):
        """Generate a crossword using baseball statistics and records"""

        # Query for statistical terms and records
        query = text("""
        WITH StatisticalTerms AS (
            SELECT 'ERA' as term, 'Earned Run Average' as description, 3 as length
            UNION SELECT 'WHIP', 'Walks plus Hits per Inning Pitched', 4
            UNION SELECT 'OPS', 'On-base Plus Slugging', 3
            UNION SELECT 'RBI', 'Runs Batted In', 3
            UNION SELECT 'GIDP', 'Grounded Into Double Play', 4
            UNION SELECT 'SLUG', 'Slugging Percentage', 4
            UNION SELECT 'SAVE', 'Pitching statistic', 4
            UNION SELECT 'BALK', 'Illegal pitching motion', 4
            UNION SELECT 'CYCLE', 'Single, double, triple, homer in one game', 5
            UNION SELECT 'TRIPLE', 'Three-base hit', 6
        ),
        RecordHolders AS (
            SELECT 
                p.nameLast as term,
                CONCAT('Career HR leader (', MAX(b.career_HR), ' HRs)') as description,
                LENGTH(p.nameLast) as length
            FROM people p
            JOIN (
                SELECT playerID, SUM(b_HR) as career_HR
                FROM batting
                GROUP BY playerID
                ORDER BY career_HR DESC
                LIMIT 1
            ) b ON p.playerID = b.playerID
            WHERE p.nameLast REGEXP '^[A-Z]+$'
            UNION
            SELECT 
                p.nameLast,
                CONCAT('Career hits leader (', MAX(b.career_hits), ' hits)'),
                LENGTH(p.nameLast)
            FROM people p
            JOIN (
                SELECT playerID, SUM(b_H) as career_hits
                FROM batting
                GROUP BY playerID
                ORDER BY career_hits DESC
                LIMIT 1
            ) b ON p.playerID = b.playerID
            WHERE p.nameLast REGEXP '^[A-Z]+$'
        ),
        AllTerms AS (
            SELECT * FROM StatisticalTerms
            UNION
            SELECT * FROM RecordHolders
            WHERE length BETWEEN 3 AND 7
        )
        SELECT term as word, description, length
        FROM AllTerms
        ORDER BY RAND()
        LIMIT 15
        """)

        terms = session_db.execute(query).fetchall()

        grid, word_positions = self._create_grid_with_intersections(terms)
        clues = self._generate_statistical_clues(session_db, word_positions)

        return {
            'theme': 'Baseball Statistics & Records',
            'grid': grid,
            'across_clues': clues['across'],
            'down_clues': clues['down'],
            'difficulty': difficulty,
            'word_positions': word_positions
        }

    def get_daily_puzzle(self, session_db):
        """Get the daily crossword puzzle"""
        days_since_epoch = (date.today() - date(2024, 1, 1)).days
        puzzle_type = days_since_epoch % 3

        if puzzle_type == 0:
            return self.generate_player_based_crossword(session_db)
        elif puzzle_type == 1:
            return self.generate_team_based_crossword(session_db)
        else:
            return self.generate_statistical_crossword(session_db)

    def _create_grid_with_intersections(self, words):
        """Create a crossword grid with word intersections"""
        grid = [[' ' for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        word_positions = {'across': {}, 'down': {}}
        used_positions = set()

        # Sort words by length (longer first)
        words_list = [(w.word if hasattr(w, 'word') else w.nameLast, w) for w in words]
        words_list.sort(key=lambda x: -len(x[0]))

        clue_num = 1
        placed_words = []

        for word, word_data in words_list:
            if self._place_word(grid, word, used_positions, placed_words):
                placed_words.append((word, word_data))

        # Assign clue numbers to placed words
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if (row, col) in used_positions:
                    # Check if this is the start of a word
                    is_across_start = (col == 0 or grid[row][col - 1] == ' ') and col < self.grid_size - 1 and \
                                      grid[row][col + 1] != ' '
                    is_down_start = (row == 0 or grid[row - 1][col] == ' ') and row < self.grid_size - 1 and \
                                    grid[row + 1][col] != ' '

                    if is_across_start or is_down_start:
                        # Find the word(s) at this position
                        for word, word_data in placed_words:
                            if is_across_start:
                                if self._word_starts_at(grid, word, row, col, 'across'):
                                    word_positions['across'][str(clue_num)] = {
                                        'word': word,
                                        'data': word_data,
                                        'row': row,
                                        'col': col,
                                        'answer': word
                                    }
                            if is_down_start:
                                if self._word_starts_at(grid, word, row, col, 'down'):
                                    word_positions['down'][str(clue_num)] = {
                                        'word': word,
                                        'data': word_data,
                                        'row': row,
                                        'col': col,
                                        'answer': word
                                    }
                        clue_num += 1

        return grid, word_positions

    def _place_word(self, grid, word, used_positions, placed_words):
        """Try to place a word in the grid"""
        if not placed_words:
            # First word - place horizontally in middle
            row = self.grid_size // 2
            col = (self.grid_size - len(word)) // 2
            for i, letter in enumerate(word):
                grid[row][col + i] = letter
                used_positions.add((row, col + i))
            return True

        # Try to intersect with existing words
        for _ in range(100):  # Max attempts
            if random.choice([True, False]):  # Horizontal
                row = random.randint(0, self.grid_size - 1)
                col = random.randint(0, self.grid_size - len(word))
                if self._can_place_horizontal(grid, word, row, col, used_positions):
                    for i, letter in enumerate(word):
                        grid[row][col + i] = letter
                        used_positions.add((row, col + i))
                    return True
            else:  # Vertical
                row = random.randint(0, self.grid_size - len(word))
                col = random.randint(0, self.grid_size - 1)
                if self._can_place_vertical(grid, word, row, col, used_positions):
                    for i, letter in enumerate(word):
                        grid[row + i][col] = letter
                        used_positions.add((row + i, col))
                    return True

        return False

    def _can_place_horizontal(self, grid, word, row, col, used_positions):
        """Check if a word can be placed horizontally"""
        if col + len(word) > self.grid_size:
            return False

        has_intersection = False
        for i, letter in enumerate(word):
            pos = (row, col + i)
            if pos in used_positions:
                if grid[row][col + i] != letter:
                    return False
                has_intersection = True
            else:
                # Check for adjacent words
                if row > 0 and grid[row - 1][col + i] != ' ':
                    return False
                if row < self.grid_size - 1 and grid[row + 1][col + i] != ' ':
                    return False

        # Check ends
        if col > 0 and grid[row][col - 1] != ' ':
            return False
        if col + len(word) < self.grid_size and grid[row][col + len(word)] != ' ':
            return False

        return has_intersection or not used_positions

    def _can_place_vertical(self, grid, word, row, col, used_positions):
        """Check if a word can be placed vertically"""
        if row + len(word) > self.grid_size:
            return False

        has_intersection = False
        for i, letter in enumerate(word):
            pos = (row + i, col)
            if pos in used_positions:
                if grid[row + i][col] != letter:
                    return False
                has_intersection = True
            else:
                # Check for adjacent words
                if col > 0 and grid[row + i][col - 1] != ' ':
                    return False
                if col < self.grid_size - 1 and grid[row + i][col + 1] != ' ':
                    return False

        # Check ends
        if row > 0 and grid[row - 1][col] != ' ':
            return False
        if row + len(word) < self.grid_size and grid[row + len(word)][col] != ' ':
            return False

        return has_intersection or not used_positions

    def _word_starts_at(self, grid, word, row, col, direction):
        """Check if a word starts at the given position"""
        if direction == 'across':
            if col + len(word) > self.grid_size:
                return False
            return all(grid[row][col + i] == word[i] for i in range(len(word)))
        else:  # down
            if row + len(word) > self.grid_size:
                return False
            return all(grid[row + i][col] == word[i] for i in range(len(word)))

    def _generate_player_clues(self, session_db, word_positions):
        """Generate clues for player-based crossword"""
        clues = {'across': {}, 'down': {}}

        for direction in ['across', 'down']:
            for num, pos_data in word_positions[direction].items():
                player_data = pos_data['data']
                playerID = player_data.playerID

                # Complex query to generate contextual clue
                query = text("""
                WITH PlayerDetails AS (
                    SELECT 
                        p.playerID,
                        p.nameFirst,
                        p.nameLast,
                        p.birthYear,
                        p.deathYear,
                        COALESCE(b.career_HR, 0) as career_HR,
                        COALESCE(b.career_hits, 0) as career_hits,
                        COALESCE(b.career_avg, 0) as career_avg,
                        COALESCE(pit.career_wins, 0) as career_wins,
                        COALESCE(pit.career_ERA, 999) as career_ERA,
                        COALESCE(a.award_count, 0) as award_count,
                        COALESCE(hof.inducted, 'N') as is_HOF,
                        t.teams_played_for
                    FROM people p
                    LEFT JOIN (
                        SELECT 
                            playerID,
                            SUM(b_HR) as career_HR,
                            SUM(b_H) as career_hits,
                            ROUND(SUM(b_H) / NULLIF(SUM(b_AB), 0), 3) as career_avg
                        FROM batting
                        GROUP BY playerID
                    ) b ON p.playerID = b.playerID
                    LEFT JOIN (
                        SELECT 
                            playerID,
                            SUM(p_W) as career_wins,
                            ROUND(SUM(p_ER) * 9 / NULLIF(SUM(p_IPOuts) / 3, 0), 2) as career_ERA
                        FROM pitching
                        GROUP BY playerID
                    ) pit ON p.playerID = pit.playerID
                    LEFT JOIN (
                        SELECT playerID, COUNT(*) as award_count
                        FROM awards
                        GROUP BY playerID
                    ) a ON p.playerID = a.playerID
                    LEFT JOIN (
                        SELECT playerID, inducted
                        FROM halloffame
                        WHERE yearID = (
                            SELECT MAX(yearID) 
                            FROM halloffame h2 
                            WHERE h2.playerID = halloffame.playerID
                        )
                    ) hof ON p.playerID = hof.playerID
                    LEFT JOIN (
                        SELECT playerID, GROUP_CONCAT(DISTINCT teamID) as teams_played_for
                        FROM appearances
                        GROUP BY playerID
                    ) t ON p.playerID = t.playerID
                    WHERE p.playerID = :playerID
                )
                SELECT * FROM PlayerDetails
                """)

                result = session_db.execute(query, {"playerID": playerID}).fetchone()

                # Generate dynamic clue based on player achievements
                if result.is_HOF == 'Y':
                    clue = f"Hall of Famer with {result.career_HR} career HRs"
                elif result.career_HR > 500:
                    clue = f"500 HR club member ({result.career_HR} total)"
                elif result.career_hits > 3000:
                    clue = f"3000 hit club member"
                elif result.career_wins > 300:
                    clue = f"300-win pitcher"
                elif result.award_count > 5:
                    clue = f"{result.award_count}-time award winner {result.nameFirst}"
                else:
                    clue = f"{result.nameFirst} of baseball ({len(pos_data['word'])})"

                clues[direction][num] = {'clue': clue, 'answer': pos_data['word'],
                                         'row': pos_data['row'], 'col': pos_data['col']}

        return clues

    def _generate_team_clues(self, session_db, word_positions):
        """Generate clues for team-based crossword"""
        clues = {'across': {}, 'down': {}}

        for direction in ['across', 'down']:
            for num, pos_data in word_positions[direction].items():
                team_data = pos_data['data']

                # Generate contextual clue
                if team_data.ws_wins > 0:
                    clue = f"{team_data.ws_wins}-time World Series champions"
                elif team_data.best_season_wins > 100:
                    clue = f"Won {team_data.best_season_wins} games in {team_data.first_year}-{team_data.last_year} era"
                else:
                    clue = f"{team_data.franchName} nickname ({len(pos_data['word'])})"

                clues[direction][num] = {'clue': clue, 'answer': pos_data['word'],
                                         'row': pos_data['row'], 'col': pos_data['col']}

        return clues

    def _generate_statistical_clues(self, session_db, word_positions):
        """Generate clues for statistical crossword"""
        clues = {'across': {}, 'down': {}}

        for direction in ['across', 'down']:
            for num, pos_data in word_positions[direction].items():
                term_data = pos_data['data']
                clue = term_data.description

                clues[direction][num] = {'clue': clue, 'answer': pos_data['word'],
                                         'row': pos_data['row'], 'col': pos_data['col']}

        return clues

    def check_solution(self, user_grid, solution_grid):
        """Check if the user's grid matches the solution"""
        if len(user_grid) != len(solution_grid):
            return False

        for i in range(len(solution_grid)):
            for j in range(len(solution_grid[i])):
                if solution_grid[i][j] != ' ':  # Only check non-empty cells
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
        else:  # down
            for i, letter in enumerate(answer):
                if row + i >= len(user_grid) or user_grid[row + i][col].upper() != letter:
                    return False

        return True

    def get_hint(self, session_db, puzzle, user_grid, hint_level):
        """Provide progressive hints using database queries"""
        empty_cells = []

        # Find all empty cells that should have letters
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if puzzle['grid'][i][j] != ' ' and user_grid[i][j] == '':
                    empty_cells.append((i, j))

        if not empty_cells:
            return None

        if hint_level == 1:
            # Give statistical hint about the puzzle
            query = text("""
            SELECT 
                COUNT(DISTINCT CASE WHEN h.inducted = 'Y' THEN p.playerID END) as hof_count,
                AVG(CASE WHEN b.b_HR IS NOT NULL THEN b.b_HR ELSE 0 END) as avg_hr,
                COUNT(DISTINCT t.teamID) as team_count
            FROM people p
            LEFT JOIN halloffame h ON p.playerID = h.playerID
            LEFT JOIN batting b ON p.playerID = b.playerID
            LEFT JOIN teams t ON p.nameLast = t.team_name
            WHERE p.nameLast IN :words OR t.team_name IN :words
            """)

            # Collect all words from the puzzle
            words = []
            for direction in ['across', 'down']:
                for clue_data in puzzle[f'{direction}_clues'].values():
                    words.append(clue_data['answer'])

            if words:  # Only execute query if we have words
                result = session_db.execute(query, {"words": tuple(words)}).fetchone()

                if result and result.hof_count is not None:
                    return {
                        'type': 'statistical_hint',
                        'message': f"This puzzle features {result.hof_count} Hall of Famers with an average of {result.avg_hr:.1f} home runs"
                    }

            # Fallback to letter reveal if query fails
            if empty_cells:
                row, col = random.choice(empty_cells)
                return {
                    'type': 'reveal_letter',
                    'row': row,
                    'col': col,
                    'letter': puzzle['grid'][row][col]
                }

        elif hint_level == 2:
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
                for num, clue_info in puzzle[f'{direction}_clues'].items():
                    if not self.check_word(user_grid, clue_info, direction):
                        # Check if this word hasn't been revealed already
                        if num not in puzzle.get('completed_words', {}).get(direction, []):
                            incomplete_words.append((direction, num, clue_info))

            if incomplete_words:
                # Choose a random incomplete word
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