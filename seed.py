"""
Seed script for Triviamania baseball database.
Populates the database with historical MLB data (1980-2019) for trivia questions.
Auto-runs on app startup; skips if data already exists.
"""
import random
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession


# ---------------------------------------------------------------------------
# Player definitions: (playerID, firstName, lastName)
# ---------------------------------------------------------------------------
PLAYERS = [
    # 1980s stars
    ("schmimi01", "Mike", "Schmidt"),
    ("murraed02", "Eddie", "Murray"),
    ("ricejim01", "Jim", "Rice"),
    ("murphda01", "Dale", "Murphy"),
    ("winfida01", "Dave", "Winfield"),
    ("brettge01", "George", "Brett"),
    ("ripkeca01", "Cal", "Ripken Jr."),
    ("cansejo01", "Jose", "Canseco"),
    ("mattido01", "Don", "Mattingly"),
    ("dawsoan01", "Andre", "Dawson"),
    ("cartega01", "Gary", "Carter"),
    ("jacksre01", "Reggie", "Jackson"),
    ("bellgeo01", "George", "Bell"),
    ("strawda01", "Darryl", "Strawberry"),
    ("gaettga01", "Gary", "Gaetti"),
    ("clarkja01", "Jack", "Clark"),
    ("oglivbe01", "Ben", "Oglivie"),
    ("armasto01", "Tony", "Armas"),
    ("kinfmdv01", "Dave", "Kingman"),
    ("boydroi01", "George", "Foster"),
    ("sandery01", "Ryne", "Sandberg"),
    ("gwynrto01", "Tony", "Gwynn"),
    ("yountro01", "Robin", "Yount"),
    ("boggswa01", "Wade", "Boggs"),
    ("puckeki01", "Kirby", "Puckett"),
    # 1990s stars
    ("bondsba01", "Barry", "Bonds"),
    ("griffke02", "Ken", "Griffey Jr."),
    ("sosasa01", "Sammy", "Sosa"),
    ("mcgwima01", "Mark", "McGwire"),
    ("thomafr04", "Frank", "Thomas"),
    ("bagweje01", "Jeff", "Bagwell"),
    ("belleal01", "Albert", "Belle"),
    ("ramirma02", "Manny", "Ramirez"),
    ("gonzaju03", "Juan", "Gonzalez"),
    ("piazzmi01", "Mike", "Piazza"),
    ("walkela01", "Larry", "Walker"),
    ("palmera01", "Rafael", "Palmeiro"),
    ("vaughmo01", "Mo", "Vaughn"),
    ("willima04", "Matt", "Williams"),
    ("jonescm04", "Chipper", "Jones"),
    ("galaran01", "Andres", "Galarraga"),
    ("thomjim02", "Jim", "Thome"),
    ("guerrvl01", "Vladimir", "Guerrero"),
    ("delgaca01", "Carlos", "Delgado"),
    ("kentje01", "Jeff", "Kent"),
    # 2000s stars
    ("rodrial01", "Alex", "Rodriguez"),
    ("pujolal01", "Albert", "Pujols"),
    ("ortizda01", "David", "Ortiz"),
    ("cabremi01", "Miguel", "Cabrera"),
    ("howarry01", "Ryan", "Howard"),
    ("beltrca01", "Carlos", "Beltran"),
    ("teixema01", "Mark", "Teixeira"),
    ("sorianal01", "Alfonso", "Soriano"),
    ("fielcpr01", "Prince", "Fielder"),
    ("berkmla01", "Lance", "Berkman"),
    ("dunnad01", "Adam", "Dunn"),
    ("bautijo02", "Jose", "Bautista"),
    ("suzukic01", "Ichiro", "Suzuki"),
    ("jeterde01", "Derek", "Jeter"),
    ("rolliji01", "Jimmy", "Rollins"),
    # 2010s stars
    ("troutmi01", "Mike", "Trout"),
    ("stantgi02", "Giancarlo", "Stanton"),
    ("harpebr03", "Bryce", "Harper"),
    ("arenano01", "Nolan", "Arenado"),
    ("donaljo02", "Josh", "Donaldson"),
    ("davisch02", "Chris", "Davis"),
    ("cruzne02", "Nelson", "Cruz"),
    ("encared01", "Edwin", "Encarnacion"),
    ("bryankr01", "Kris", "Bryant"),
    ("judgear01", "Aaron", "Judge"),
    ("bettsmo01", "Mookie", "Betts"),
    ("freemfr01", "Freddie", "Freeman"),
    ("goldlpa01", "Paul", "Goldschmidt"),
    ("machama01", "Manny", "Machado"),
    ("yelic001", "Christian", "Yelich"),
    ("altuvjo01", "Jose", "Altuve"),
    ("lindofr01", "Francisco", "Lindor"),
    ("martijd02", "J.D.", "Martinez"),
    ("acunaro01", "Ronald", "Acuna Jr."),
    ("bellico01", "Cody", "Bellinger"),
    ("sotoju01", "Juan", "Soto"),
]

# ---------------------------------------------------------------------------
# Career definitions for batting data generation
# (playerID, start_year, end_year, avg_HR, avg_AB, avg_RBI)
# Stats will be generated with random variation around these averages.
# ---------------------------------------------------------------------------
CAREERS = [
    # 1980s
    ("schmimi01", 1980, 1989, 33, 520, 95),
    ("murraed02", 1980, 1996, 27, 560, 93),
    ("ricejim01", 1980, 1989, 22, 530, 85),
    ("murphda01", 1980, 1993, 28, 550, 90),
    ("winfida01", 1980, 1992, 24, 555, 90),
    ("brettge01", 1980, 1993, 18, 545, 85),
    ("ripkeca01", 1982, 2001, 23, 600, 84),
    ("cansejo01", 1986, 2001, 33, 500, 95),
    ("mattido01", 1984, 1995, 20, 570, 90),
    ("dawsoan01", 1980, 1996, 22, 540, 80),
    ("cartega01", 1980, 1992, 22, 510, 80),
    ("jacksre01", 1980, 1987, 27, 480, 80),
    ("bellgeo01", 1983, 1993, 22, 560, 90),
    ("strawda01", 1983, 1999, 28, 480, 80),
    ("gaettga01", 1982, 1993, 20, 530, 78),
    ("clarkja01", 1980, 1992, 24, 450, 82),
    ("oglivbe01", 1980, 1986, 22, 530, 80),
    ("armasto01", 1980, 1989, 24, 510, 75),
    ("kinfmdv01", 1980, 1986, 30, 430, 75),
    ("boydroi01", 1980, 1986, 22, 510, 80),
    ("sandery01", 1982, 1997, 20, 570, 75),
    ("gwynrto01", 1982, 2001, 10, 590, 60),
    ("yountro01", 1980, 1993, 15, 580, 75),
    ("boggswa01", 1982, 1999, 8, 590, 60),
    ("puckeki01", 1984, 1995, 16, 580, 80),
    # 1990s
    ("bondsba01", 1986, 2007, 38, 480, 105),
    ("griffke02", 1989, 2010, 35, 540, 100),
    ("sosasa01", 1989, 2007, 35, 540, 100),
    ("mcgwima01", 1987, 2001, 40, 420, 95),
    ("thomafr04", 1990, 2008, 32, 520, 100),
    ("bagweje01", 1991, 2005, 30, 540, 105),
    ("belleal01", 1989, 2000, 34, 530, 108),
    ("ramirma02", 1993, 2011, 35, 530, 110),
    ("gonzaju03", 1989, 2005, 32, 520, 105),
    ("piazzmi01", 1992, 2007, 30, 480, 95),
    ("walkela01", 1989, 2005, 25, 500, 85),
    ("palmera01", 1986, 2005, 30, 560, 95),
    ("vaughmo01", 1991, 2003, 30, 520, 100),
    ("willima04", 1987, 2003, 25, 520, 85),
    ("jonescm04", 1993, 2012, 28, 530, 95),
    ("galaran01", 1985, 2004, 25, 510, 85),
    ("thomjim02", 1991, 2012, 35, 480, 95),
    ("guerrvl01", 1996, 2011, 30, 560, 100),
    ("delgaca01", 1993, 2009, 32, 520, 100),
    ("kentje01", 1992, 2008, 22, 555, 90),
    # 2000s
    ("rodrial01", 1994, 2016, 38, 540, 110),
    ("pujolal01", 2001, 2019, 35, 550, 110),
    ("ortizda01", 1997, 2016, 32, 500, 100),
    ("cabremi01", 2003, 2019, 30, 555, 100),
    ("howarry01", 2004, 2016, 35, 490, 105),
    ("beltrca01", 1998, 2017, 25, 545, 90),
    ("teixema01", 2003, 2016, 30, 530, 95),
    ("sorianal01", 1999, 2014, 28, 555, 85),
    ("fielcpr01", 2005, 2016, 30, 530, 95),
    ("berkmla01", 1999, 2013, 28, 490, 95),
    ("dunnad01", 2001, 2014, 35, 460, 80),
    ("bautijo02", 2004, 2018, 28, 500, 85),
    ("suzukic01", 2001, 2019, 10, 630, 55),
    ("jeterde01", 1995, 2014, 15, 600, 70),
    ("rolliji01", 2000, 2016, 15, 610, 65),
    # 2010s
    ("troutmi01", 2011, 2019, 35, 530, 95),
    ("stantgi02", 2010, 2019, 32, 500, 90),
    ("harpebr03", 2012, 2019, 28, 490, 85),
    ("arenano01", 2013, 2019, 35, 560, 110),
    ("donaljo02", 2010, 2019, 28, 520, 85),
    ("davisch02", 2008, 2019, 28, 470, 75),
    ("cruzne02", 2005, 2019, 30, 510, 85),
    ("encared01", 2005, 2019, 30, 510, 90),
    ("bryankr01", 2015, 2019, 28, 530, 80),
    ("judgear01", 2016, 2019, 38, 480, 85),
    ("bettsmo01", 2014, 2019, 25, 570, 80),
    ("freemfr01", 2010, 2019, 24, 560, 85),
    ("goldlpa01", 2011, 2019, 28, 540, 90),
    ("machama01", 2012, 2019, 28, 550, 85),
    ("yelic001", 2013, 2019, 22, 540, 75),
    ("altuvjo01", 2011, 2019, 14, 600, 55),
    ("lindofr01", 2015, 2019, 25, 560, 75),
    ("martijd02", 2011, 2019, 30, 510, 90),
    ("acunaro01", 2018, 2019, 30, 530, 85),
    ("bellico01", 2017, 2019, 28, 520, 80),
    ("sotoju01", 2018, 2019, 25, 500, 80),
]

# ---------------------------------------------------------------------------
# Famous season overrides - these replace generated stats for iconic years
# (playerID, year, HR, AB, RBI)
# ---------------------------------------------------------------------------
FAMOUS_SEASONS = [
    # Iconic HR seasons
    ("bondsba01", 2001, 73, 476, 137),
    ("mcgwima01", 1998, 70, 509, 147),
    ("sosasa01", 1998, 66, 643, 158),
    ("mcgwima01", 1999, 65, 521, 147),
    ("sosasa01", 2001, 64, 577, 160),
    ("sosasa01", 1999, 63, 625, 141),
    ("judgear01", 2017, 52, 542, 114),
    ("rodrial01", 2002, 57, 624, 142),
    ("rodrial01", 2001, 52, 632, 135),
    ("griffke02", 1997, 56, 608, 147),
    ("griffke02", 1998, 56, 633, 146),
    ("bondsba01", 2000, 49, 480, 106),
    ("belleal01", 1995, 50, 546, 126),
    ("schmimi01", 1980, 48, 548, 121),
    ("stantgi02", 2017, 59, 597, 132),
    ("davisch02", 2013, 53, 584, 138),
    ("harpebr03", 2015, 42, 521, 99),
    ("troutmi01", 2019, 45, 470, 104),
    ("arenano01", 2015, 42, 616, 130),
    ("arenano01", 2016, 41, 618, 133),
    ("donaljo02", 2015, 41, 620, 123),
    ("cansejo01", 1988, 42, 610, 124),
    # Triple Crown - Cabrera 2012
    ("cabremi01", 2012, 44, 622, 139),
    # Pujols prime years
    ("pujolal01", 2006, 49, 535, 137),
    ("pujolal01", 2003, 43, 591, 124),
    ("pujolal01", 2004, 46, 592, 123),
    ("pujolal01", 2009, 47, 568, 135),
    # Howard MVP
    ("howarry01", 2006, 58, 581, 149),
    # Bautista breakout
    ("bautijo02", 2010, 54, 569, 124),
    ("bautijo02", 2011, 43, 513, 103),
    # Thomas MVP years
    ("thomafr04", 1994, 38, 399, 101),
    ("thomafr04", 1993, 41, 549, 128),
    # Bagwell MVP
    ("bagweje01", 1994, 39, 400, 116),
    # Mattingly
    ("mattido01", 1985, 35, 652, 145),
    # Ripken MVP
    ("ripkeca01", 1991, 34, 650, 114),
    # Bonds 90s
    ("bondsba01", 1993, 46, 539, 123),
    ("bondsba01", 1996, 42, 517, 129),
    # McGwire early
    ("mcgwima01", 1987, 49, 557, 118),
    # Gonzalez
    ("gonzaju03", 1998, 45, 606, 157),
    ("gonzaju03", 2001, 35, 532, 142),
    # Ramirez
    ("ramirma02", 1999, 44, 522, 165),
    ("ramirma02", 2001, 41, 529, 125),
    # Guerrero MVP
    ("guerrvl01", 2000, 44, 571, 123),
    ("guerrvl01", 2004, 39, 612, 126),
    # Thome
    ("thomjim02", 2002, 52, 480, 118),
    ("thomjim02", 2001, 49, 526, 124),
    # Ortiz
    ("ortizda01", 2006, 54, 558, 137),
    # Fielder
    ("fielcpr01", 2007, 50, 573, 119),
    # Encarnacion
    ("encared01", 2012, 42, 542, 110),
    # Cruz
    ("cruzne02", 2014, 40, 613, 108),
    # Bryant ROY/MVP
    ("bryankr01", 2016, 39, 603, 102),
    # Yelich MVP
    ("yelic001", 2018, 36, 574, 110),
    ("yelic001", 2019, 44, 489, 97),
    # Bellinger MVP
    ("bellico01", 2019, 47, 558, 115),
    # Acuna
    ("acunaro01", 2019, 41, 626, 101),
    # Soto
    ("sotoju01", 2019, 34, 542, 110),
]

# ---------------------------------------------------------------------------
# MLB Teams with era-based win tendencies
# (team_name, start_year, end_year, base_wins, variation)
# ---------------------------------------------------------------------------
TEAM_ERAS = [
    # Consistently strong franchises
    ("New York Yankees", 1980, 2019, 90, 12),
    ("Los Angeles Dodgers", 1980, 2019, 87, 11),
    ("St. Louis Cardinals", 1980, 2019, 86, 10),
    ("Atlanta Braves", 1980, 2019, 84, 13),
    ("Boston Red Sox", 1980, 2019, 85, 12),
    ("Oakland Athletics", 1980, 2019, 82, 14),
    # Strong in certain eras
    ("Toronto Blue Jays", 1980, 2019, 80, 14),
    ("San Francisco Giants", 1980, 2019, 82, 12),
    ("Houston Astros", 1980, 2019, 80, 15),
    ("Cleveland Indians", 1980, 2019, 79, 14),
    ("Minnesota Twins", 1980, 2019, 78, 14),
    ("Chicago White Sox", 1980, 2019, 79, 13),
    ("Cincinnati Reds", 1980, 2019, 79, 13),
    ("Philadelphia Phillies", 1980, 2019, 79, 14),
    ("New York Mets", 1980, 2019, 78, 15),
    ("Baltimore Orioles", 1980, 2019, 76, 16),
    ("Chicago Cubs", 1980, 2019, 78, 14),
    ("Texas Rangers", 1980, 2019, 78, 13),
    ("Detroit Tigers", 1980, 2019, 78, 14),
    ("Los Angeles Angels", 1980, 2019, 79, 12),
    ("Milwaukee Brewers", 1980, 2019, 77, 13),
    ("Kansas City Royals", 1980, 2019, 76, 15),
    ("Pittsburgh Pirates", 1980, 2019, 76, 14),
    ("San Diego Padres", 1980, 2019, 75, 13),
    ("Seattle Mariners", 1980, 2019, 74, 15),
    ("Washington Nationals", 2005, 2019, 79, 14),
    ("Montreal Expos", 1980, 2004, 77, 13),
    ("Arizona Diamondbacks", 1998, 2019, 78, 15),
    ("Colorado Rockies", 1993, 2019, 74, 14),
    ("Tampa Bay Rays", 1998, 2019, 76, 16),
    ("Miami Marlins", 1993, 2019, 72, 16),
]

# Famous team-season overrides: (team, year, wins)
FAMOUS_TEAM_SEASONS = [
    ("New York Yankees", 1998, 114),
    ("Seattle Mariners", 2001, 116),
    ("Chicago Cubs", 2016, 103),
    ("Atlanta Braves", 1998, 106),
    ("Cleveland Indians", 1995, 100),
    ("New York Yankees", 2001, 95),
    ("Boston Red Sox", 2004, 98),
    ("Boston Red Sox", 2018, 108),
    ("Houston Astros", 2017, 101),
    ("Houston Astros", 2019, 107),
    ("Los Angeles Dodgers", 2017, 104),
    ("Los Angeles Dodgers", 2019, 106),
    ("St. Louis Cardinals", 2004, 105),
    ("San Francisco Giants", 2010, 92),
    ("Philadelphia Phillies", 2008, 92),
    ("Philadelphia Phillies", 1980, 91),
    ("Detroit Tigers", 1984, 104),
    ("New York Mets", 1986, 108),
    ("Oakland Athletics", 1988, 104),
    ("Oakland Athletics", 1989, 99),
    ("Minnesota Twins", 1987, 85),
    ("Toronto Blue Jays", 1992, 96),
    ("Toronto Blue Jays", 1993, 95),
    ("Baltimore Orioles", 1983, 98),
    ("Kansas City Royals", 1985, 91),
    ("Cincinnati Reds", 1990, 91),
    ("Arizona Diamondbacks", 2001, 92),
    ("Chicago White Sox", 2005, 99),
    ("Tampa Bay Rays", 2008, 97),
    ("Washington Nationals", 2019, 93),
    ("Cleveland Indians", 2017, 102),
    ("New York Yankees", 2019, 103),
    ("Los Angeles Dodgers", 2020, 43),  # Shortened season
]


def _generate_batting_data():
    """Generate batting records from career definitions + famous season overrides."""
    rng = random.Random(42)  # Fixed seed for reproducible data

    # Index famous seasons for fast lookup
    famous = {}
    for pid, year, hr, ab, rbi in FAMOUS_SEASONS:
        famous[(pid, year)] = (hr, ab, rbi)

    records = []
    for pid, start, end, avg_hr, avg_ab, avg_rbi in CAREERS:
        for year in range(start, end + 1):
            if (pid, year) in famous:
                hr, ab, rbi = famous[(pid, year)]
            else:
                hr = max(0, avg_hr + rng.randint(-10, 10))
                ab = max(200, avg_ab + rng.randint(-60, 40))
                rbi = max(10, avg_rbi + rng.randint(-20, 20))
            records.append((pid, year, hr, ab, rbi))

    return records


def _generate_team_data():
    """Generate team win records from era definitions + famous season overrides."""
    rng = random.Random(99)

    famous = {}
    for team, year, wins in FAMOUS_TEAM_SEASONS:
        famous[(team, year)] = wins

    records = []
    for team, start, end, base_w, var in TEAM_ERAS:
        for year in range(start, end + 1):
            if (team, year) in famous:
                wins = famous[(team, year)]
            else:
                wins = max(50, min(110, base_w + rng.randint(-var, var)))
            records.append((team, year, wins))

    return records


def seed_database(engine):
    """Seed baseball data if the database is empty. Safe to call multiple times."""
    with DBSession(engine) as session:
        try:
            count = session.execute(text("SELECT COUNT(*) FROM people")).scalar()
            if count and count > 0:
                return  # Already seeded
        except Exception:
            return  # Table might not exist yet on first import; will seed next restart

        print("Seeding baseball data...")

        # Insert players
        for pid, first, last in PLAYERS:
            session.execute(
                text("INSERT INTO people (playerID, nameFirst, nameLast) VALUES (:p, :f, :l)"),
                {"p": pid, "f": first, "l": last},
            )

        # Insert batting records
        batting_data = _generate_batting_data()
        for pid, year, hr, ab, rbi in batting_data:
            session.execute(
                text("INSERT INTO batting (playerID, yearID, b_HR, b_AB, b_RBI) VALUES (:p, :y, :hr, :ab, :rbi)"),
                {"p": pid, "y": year, "hr": hr, "ab": ab, "rbi": rbi},
            )

        # Insert team records
        team_data = _generate_team_data()
        for team, year, wins in team_data:
            session.execute(
                text("INSERT INTO teams (team_name, yearID, team_W) VALUES (:t, :y, :w)"),
                {"t": team, "y": year, "w": wins},
            )

        # Create demo accounts
        from werkzeug.security import generate_password_hash

        session.execute(
            text("INSERT INTO users (username, password_hash, is_admin, is_banned) VALUES (:u, :p, :a, :b)"),
            {"u": "admin", "p": generate_password_hash("demo123"), "a": True, "b": False},
        )
        session.execute(
            text("INSERT INTO users (username, password_hash, is_admin, is_banned) VALUES (:u, :p, :a, :b)"),
            {"u": "guest", "p": generate_password_hash("guest123"), "a": False, "b": False},
        )

        session.commit()
        print(f"  Seeded {len(PLAYERS)} players, {len(batting_data)} batting records, {len(team_data)} team records.")
        print("  Demo accounts: admin/demo123 (admin), guest/guest123 (player)")


if __name__ == "__main__":
    from app import engine
    seed_database(engine)
