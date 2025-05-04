import random
from datetime import date
import json
from sqlalchemy import text


class BaseballConnections:
    def __init__(self):
        self.max_mistakes = 4
        self.group_size = 4
        self.total_items = 16

        self.difficulty_levels = {
            1: "Easy",
            2: "Medium",
            3: "Hard",
            4: "Very Hard"
        }

    def get_players_by_criteria(self, session_db, criteria, limit=4):
        """Get players matching specific criteria from database"""
        queries = {
            "500_home_run_club": """
            SELECT DISTINCT p.nameLast 
            FROM people p
            JOIN batting b ON p.playerID = b.playerID
            GROUP BY p.playerID, p.nameLast
            HAVING SUM(b.b_HR) >= 500
            ORDER BY SUM(b.b_HR) DESC
            LIMIT :limit
        """,

        "3000_hit_club": """
            SELECT DISTINCT p.nameLast 
            FROM people p
            JOIN batting b ON p.playerID = b.playerID
            GROUP BY p.playerID, p.nameLast
            HAVING SUM(b.b_H) >= 3000
            ORDER BY SUM(b.b_H) DESC
            LIMIT :limit
        """,

            "left_handed_legends": """
                SELECT DISTINCT p.nameLast 
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                WHERE p.bats = 'L'
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_HR) >= 300
                ORDER BY SUM(b.b_HR) DESC
                LIMIT :limit
            """,

            "switch_hitters": """
                SELECT DISTINCT p.nameLast 
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                WHERE p.bats = 'B'
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_H) >= 2000
                ORDER BY SUM(b.b_H) DESC
                LIMIT :limit
            """,

            "pitchers_who_hit": """
                SELECT DISTINCT p.nameLast 
                FROM people p
                JOIN pitching pi ON p.playerID = pi.playerID
                JOIN batting b ON p.playerID = b.playerID
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(pi.p_W) >= 50 AND SUM(b.b_HR) >= 20
                LIMIT :limit
            """,

            "stolen_base_kings": """
                SELECT DISTINCT p.nameLast 
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_SB) >= 400
                ORDER BY SUM(b.b_SB) DESC
                LIMIT :limit
            """,

            "world_series_teams": """
                SELECT DISTINCT t.team_name 
                FROM teams t
                JOIN seriespost s ON t.teamID = s.teamIDwinner
                WHERE s.round = 'WS' AND t.team_name IS NOT NULL
                ORDER BY RAND()
                LIMIT :limit
            """,

            "original_teams": """
                SELECT DISTINCT franchName
                FROM franchises
                WHERE active = 'Y' AND franchID IN (
                    SELECT franchID FROM teams WHERE yearID = 1901
                )
                ORDER BY RAND()
                LIMIT :limit
            """,

            "MVP_winners": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN awards a ON p.playerID = a.playerID
                WHERE a.awardID = 'Most Valuable Player'
                GROUP BY p.playerID, p.nameLast
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            """,

            "cy_young_winners": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN awards a ON p.playerID = a.playerID
                WHERE a.awardID = 'Cy Young Award'
                GROUP BY p.playerID, p.nameLast
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            """,

            "hall_of_fame_catchers": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN halloffame h ON p.playerID = h.playerID
                JOIN fielding f ON p.playerID = f.playerID
                WHERE h.inducted = 'Y' AND f.position = 'C'
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(f.f_G) >= 500
                LIMIT :limit
            """,

            "modern_sluggers": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN batting b ON p.playerID = b.playerID
                WHERE b.yearId >= 2000
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(b.b_HR) >= 300
                ORDER BY SUM(b.b_HR) DESC
                LIMIT :limit
            """,

            "famous_stadiums": """
                SELECT DISTINCT park_name
                FROM parks
                WHERE park_name IN ('Fenway Park', 'Wrigley Field', 'Yankee Stadium', 'Dodger Stadium')
                ORDER BY RAND()
                LIMIT :limit
            """,

            "300_game_winners": """
                SELECT DISTINCT p.nameLast
                FROM people p
                JOIN pitching pi ON p.playerID = pi.playerID
                GROUP BY p.playerID, p.nameLast
                HAVING SUM(pi.p_W) >= 300
                ORDER BY SUM(pi.p_W) DESC
                LIMIT :limit
            """
        }

        if criteria in queries:
            query = text(queries[criteria])
            results = session_db.execute(query, {"limit": limit}).fetchall()
            items = [row[0] for row in results if row[0]]

            print(f"DEBUG: Query {criteria} returned {len(items)} items: {items}")

            return items
        return []

    def get_daily_puzzle(self, session_db):
        """Generate a daily puzzle based on the date using database"""
        today = date.today()
        random.seed(today.strftime("%Y%m%d"))

        # Database-driven categories
        categories_pool = {
            "500 Home Run Club": ("500_home_run_club", "Players who hit 500+ career home runs"),
            "3,000 Hit Club": ("3000_hit_club", "Players with 3,000+ career hits"),
            "Left-Handed Legends": ("left_handed_legends", "Famous left-handed batters"),
            "Switch Hitters": ("switch_hitters", "Notable switch-hitting players"),
            "Pitchers Who Could Hit": ("pitchers_who_hit", "Pitchers known for their batting"),
            "Stolen Base Kings": ("stolen_base_kings", "Players with 400+ stolen bases"),
            "World Series Winners": ("world_series_teams", "Teams that won the World Series"),
            "Original MLB Teams": ("original_teams", "Teams from MLB's early years"),
            "MVP Winners": ("MVP_winners", "Multiple MVP award winners"),
            "Cy Young Winners": ("cy_young_winners", "Multiple Cy Young award winners"),
            "HOF Catchers": ("hall_of_fame_catchers", "Hall of Fame catchers"),
            "Modern Sluggers": ("modern_sluggers", "21st century home run leaders"),
            "Historic Ballparks": ("famous_stadiums", "Famous baseball stadiums"),
            "300 Game Winners": ("300_game_winners", "Pitchers with 300+ wins"),
            "Baseball Terms": ("baseball_terms", "Common baseball terms")
        }

        # Keep track of all used items to avoid duplicates
        used_items = set()
        puzzle = {
            "categories": {},
            "puzzle_items": [],
            "date": today.strftime("%Y-%m-%d")
        }

        # Select 4 random categories
        selected_categories = random.sample(list(categories_pool.keys()), 4)

        for i, category in enumerate(selected_categories):
            difficulty = i + 1
            criteria = categories_pool[category][0]
            description = categories_pool[category][1]

            # Get items for this category
            if criteria == "baseball_terms":
                potential_items = ["STRIKE", "BALL", "HOME", "BASE", "OUT", "SAFE", "FOUL", "BUNT"]
            else:
                potential_items = self.get_players_by_criteria(session_db, criteria, 10)  # Get more than needed

            # Filter out already used items
            available_items = [item for item in potential_items if item not in used_items]

            # If not enough unique items, get from fallback
            if len(available_items) < 4:
                fallback_items = ["AARON", "RUTH", "MAYS", "BONDS", "JETER", "TROUT", "MANTLE", "GIBSON",
                                  "KOUFAX", "CLEMENTE", "ROBINSON", "WILLIAMS", "DIMAGGIO", "GEHRIG"]
                fallback_items = [item for item in fallback_items if item not in used_items]
                random.shuffle(fallback_items)
                available_items.extend(fallback_items[:4 - len(available_items)])

            # Take exactly 4 items
            selected_items = available_items[:4]

            # Add to used items set
            used_items.update(selected_items)

            puzzle["categories"][category] = {
                "items": selected_items,
                "difficulty": difficulty,
                "difficulty_name": self.difficulty_levels[difficulty],
                "description": description
            }
            puzzle["puzzle_items"].extend(selected_items)

        # Shuffle the items
        random.shuffle(puzzle["puzzle_items"])

        print(f"DEBUG: Final puzzle: {puzzle}")  # Debug print

        return puzzle

    def check_guess(self, selected_items, puzzle):
        """Check if the selected items form a valid group"""
        if len(selected_items) != self.group_size:
            return False, None, None

        for category, data in puzzle["categories"].items():
            if set(selected_items) == set(data["items"]):
                return True, category, data["difficulty"]

        return False, None, None