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

        # Hardcoded fallback categories for when DB queries fail
        self._fallback_categories = {
            "500 Home Run Club": {
                "items": ["AARON", "RUTH", "MAYS", "BONDS", "SOSA", "MANTLE", "GRIFFEY", "ROBINSON"],
                "description": "Players who hit 500+ career home runs"
            },
            "3,000 Hit Club": {
                "items": ["ROSE", "COBB", "JETER", "MOLITOR", "CAREW", "YOUNT", "MURRAY", "RIPKEN"],
                "description": "Players with 3,000+ career hits"
            },
            "MVP Winners": {
                "items": ["TROUT", "BERRA", "DIMAGGIO", "SCHMIDT", "MUSIAL", "GEHRIG", "FOXX", "BANKS"],
                "description": "Multiple MVP award winners"
            },
            "Modern Sluggers": {
                "items": ["PUJOLS", "ORTIZ", "CABRERA", "THOME", "DUNN", "HOWARD", "STANTON", "JUDGE"],
                "description": "21st century home run leaders"
            },
            "Baseball Terms": {
                "items": ["STRIKE", "BALL", "HOME", "BASE", "OUT", "SAFE", "FOUL", "BUNT"],
                "description": "Common baseball terms"
            },
            "Stolen Base Kings": {
                "items": ["HENDERSON", "BROCK", "COLEMAN", "RAINES", "LOFTON", "WILLS", "MORGAN", "PIERRE"],
                "description": "Players with 400+ stolen bases"
            },
            "Historic Ballparks": {
                "items": ["FENWAY", "WRIGLEY", "DODGER", "YANKEE", "CAMDEN", "SHEA", "POLO", "COMISKEY"],
                "description": "Famous baseball stadiums"
            },
            "World Series Winners": {
                "items": ["YANKEES", "CARDINALS", "RED SOX", "GIANTS", "DODGERS", "ATHLETICS", "BRAVES", "REDS"],
                "description": "Teams that won the World Series"
            },
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
        }

        if criteria in queries:
            try:
                query = text(queries[criteria])
                results = session_db.execute(query, {"limit": limit}).fetchall()
                items = [row[0] for row in results if row[0]]
                return items
            except Exception:
                try:
                    session_db.rollback()
                except Exception:
                    pass
        return []

    def get_daily_puzzle(self, session_db):
        """Generate a daily puzzle based on the date using database"""
        today = date.today()
        random.seed(today.strftime("%Y%m%d"))

        # Keep track of all used items to avoid duplicates
        used_items = set()
        puzzle = {
            "categories": {},
            "puzzle_items": [],
            "date": today.strftime("%Y-%m-%d")
        }

        # Select 4 random categories from fallback pool
        selected_categories = random.sample(list(self._fallback_categories.keys()), 4)

        for i, category in enumerate(selected_categories):
            difficulty = i + 1
            cat_data = self._fallback_categories[category]

            # Try DB first for categories that have queries
            criteria_map = {
                "500 Home Run Club": "500_home_run_club",
                "3,000 Hit Club": "3000_hit_club",
                "Modern Sluggers": "modern_sluggers",
            }

            potential_items = []
            if category in criteria_map:
                potential_items = self.get_players_by_criteria(
                    session_db, criteria_map[category], 10
                )

            # Fall back to hardcoded items if DB didn't return enough
            if len(potential_items) < 4:
                potential_items = list(cat_data["items"])
                random.shuffle(potential_items)

            # Filter out already used items
            available_items = [item for item in potential_items if item not in used_items]

            # If still not enough, add generic fallback names
            if len(available_items) < 4:
                fallback_items = ["AARON", "RUTH", "MAYS", "BONDS", "JETER", "TROUT",
                                  "MANTLE", "GIBSON", "KOUFAX", "CLEMENTE", "ROBINSON",
                                  "WILLIAMS", "DIMAGGIO", "GEHRIG"]
                fallback_items = [item for item in fallback_items if item not in used_items]
                random.shuffle(fallback_items)
                available_items.extend(fallback_items[:4 - len(available_items)])

            # Take exactly 4 items
            selected_items = available_items[:4]
            used_items.update(selected_items)

            puzzle["categories"][category] = {
                "items": selected_items,
                "difficulty": difficulty,
                "difficulty_name": self.difficulty_levels[difficulty],
                "description": cat_data["description"]
            }
            puzzle["puzzle_items"].extend(selected_items)

        # Shuffle the items
        random.shuffle(puzzle["puzzle_items"])

        return puzzle

    def check_guess(self, selected_items, puzzle):
        """Check if the selected items form a valid group"""
        if len(selected_items) != self.group_size:
            return False, None, None

        for category, data in puzzle["categories"].items():
            if set(selected_items) == set(data["items"]):
                return True, category, data["difficulty"]

        return False, None, None
