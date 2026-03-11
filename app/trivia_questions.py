from sqlalchemy import text, bindparam
import random
import logging

# Batting Statistics Mapping
batting_stat_mapping = {
    'b_G': 'Games Played',
    'b_AB': 'At Bats',
    'b_R': 'Runs Scored',
    'b_H': 'Hits',
    'b_2B': 'Doubles',
    'b_3B': 'Triples',
    'b_HR': 'Home Runs',
    'b_RBI': 'Runs Batted In',
    'b_SB': 'Stolen Bases',
    'b_CS': 'Caught Stealing',
    'b_BB': 'Walks',
    'b_SO': 'Strikeouts',
    'b_IBB': 'Intentional Walks',
    'b_HBP': 'Hit By Pitch',
    'b_SH': 'Sacrifice Hits',
    'b_SF': 'Sacrifice Flies',
    'b_GIDP': 'Double Plays Grounded Into'
}

# Pitching Statistics Mapping
pitching_stat_mapping = {
    'p_W': 'Wins',
    'p_L': 'Losses',
    'p_G': 'Games Pitched',
    'p_GS': 'Games Started',
    'p_CG': 'Complete Games',
    'p_SHO': 'Shutouts',
    'p_SV': 'Saves',
    'p_IPOuts': 'Innings Pitched (Outs)',
    'p_H': 'Hits Allowed',
    'p_ER': 'Earned Runs',
    'p_HR': 'Home Runs Allowed',
    'p_BB': 'Walks Allowed',
    'p_SO': 'Strikeouts',
    'p_BAOpp': 'Opponent Batting Average',
    'p_ERA': 'Earned Run Average',
    'p_IBB': 'Intentional Walks Allowed',
    'p_WP': 'Wild Pitches',
    'p_HBP': 'Batters Hit By Pitch',
    'p_BK': 'Balks',
    'p_BFP': 'Batters Faced',
    'p_GF': 'Games Finished',
    'p_R': 'Runs Allowed',
    'p_SH': 'Sacrifice Hits Allowed',
    'p_SF': 'Sacrifice Flies Allowed',
    'p_GIDP': 'Double Plays Induced'
}

# Team Statistics Mapping
team_stat_mapping = {
    'team_G': 'Games Played',
    'team_G_home': 'Home Games',
    'team_W': 'Wins',
    'team_L': 'Losses',
    'team_R': 'Runs Scored',
    'team_AB': 'Team At Bats',
    'team_H': 'Team Hits',
    'team_2B': 'Team Doubles',
    'team_3B': 'Team Triples',
    'team_HR': 'Team Home Runs',
    'team_BB': 'Team Walks',
    'team_SO': 'Team Strikeouts',
    'team_SB': 'Team Stolen Bases',
    'team_CS': 'Team Caught Stealing',
    'team_HBP': 'Team Hit By Pitch',
    'team_SF': 'Team Sacrifice Flies',
    'team_RA': 'Runs Allowed',
    'team_ER': 'Earned Runs Allowed',
    'team_ERA': 'Team ERA',
    'team_CG': 'Complete Games',
    'team_SHO': 'Shutouts',
    'team_SV': 'Saves',
    'team_E': 'Errors',
    'team_DP': 'Double Plays',
    'team_FP': 'Fielding Percentage',
    'team_attendance': 'Home Attendance'
}


def _safe_rollback(session_db):
    """Rollback session after a failed query so subsequent queries work."""
    try:
        session_db.rollback()
    except Exception:
        pass


def generate_player_stat_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a trivia question about player batting statistics for a given year.
    """
    # Year selection based on difficulty
    if difficulty == 'easy':
        year = random.choice(range(2005, 2020))
    elif difficulty == 'medium':
        year = random.choice(range(1990, 2020))
    else:  # hard
        year = random.choice(range(1980, 2020))

    # Stat selection based on difficulty
    if difficulty == 'easy':
        common_stats = ['b_HR', 'b_RBI', 'b_H']
    elif difficulty == 'medium':
        common_stats = ['b_HR', 'b_RBI', 'b_H', 'b_R', 'b_SB']
    else:  # hard
        common_stats = ['b_HR', 'b_RBI', 'b_H', 'b_R', 'b_SB', 'b_BB', 'b_2B', 'b_3B', 'b_IBB']

    stat_type = random.choice(common_stats)
    stat_name = batting_stat_mapping[stat_type]

    query = text(f"""
        SELECT playerID, {stat_type} FROM batting
        WHERE yearID = :year AND {stat_type} IS NOT NULL
        ORDER BY {stat_type} DESC LIMIT 4
    """)
    try:
        results = session_db.execute(query, {"year": year}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_player_stat_question: {e}")
        _safe_rollback(session_db)
        return None

    if not results or len(results) < 2:
        logging.warning(f"No results found for player stat question with year={year}, stat_type={stat_type}")
        return None

    correct = results[0]
    correct_player_id = correct[0]
    options_data = list(results[:4])
    random.shuffle(options_data)

    options_player_ids = [opt[0] for opt in options_data]
    name_query = text(
        "SELECT playerID, nameFirst, nameLast FROM people WHERE playerID IN :pids"
    ).bindparams(bindparam("pids", expanding=True))
    try:
        name_results = session_db.execute(name_query, {"pids": options_player_ids}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_player_stat_question (name query): {e}")
        _safe_rollback(session_db)
        return None

    player_names = {row[0]: f"{row[1]} {row[2]}" for row in name_results}
    options = [(pid, value) for pid, value in options_data if pid in player_names]

    if len(options) < 2:
        logging.warning(
            f"Not enough valid options found for player stat question with year={year}, stat_type={stat_type}")
        return None

    answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
    correct_letter = [k for k, v in answer_map.items() if v == correct[0]][0]
    correct_answer_name = player_names.get(correct[0], correct[0])

    question_id_str = f"player_stat_{year}_{stat_type}_{correct_player_id}"
    question_id = hash(question_id_str)

    if asked_question_ids and question_id in asked_question_ids:
        return None

    return {
        "type": "player_stat",
        "question": f"Who led the league in {stat_name} in {year}?",
        "options": {k: player_names.get(v, v) for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": correct_answer_name,
        "question_id": question_id
    }


def generate_pitcher_stat_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a trivia question about pitcher statistics for a given year.
    """
    # Year selection based on difficulty
    if difficulty == 'easy':
        year = random.choice(range(2005, 2020))
    elif difficulty == 'medium':
        year = random.choice(range(1990, 2020))
    else:  # hard
        year = random.choice(range(1980, 2020))

    # Stat selection based on difficulty
    if difficulty == 'easy':
        common_stats = ['p_W', 'p_ERA', 'p_SO']
    elif difficulty == 'medium':
        common_stats = ['p_W', 'p_ERA', 'p_SO', 'p_SV', 'p_CG']
    else:  # hard
        common_stats = ['p_W', 'p_ERA', 'p_SO', 'p_SV', 'p_CG', 'p_SHO', 'p_H', 'p_HR']

    stat_type = random.choice(common_stats)
    stat_name = pitching_stat_mapping[stat_type]

    # For ERA, we want the LOWEST value, not highest
    if stat_type == 'p_ERA':
        order_direction = "ASC"
        question_format = "Which pitcher had the lowest {stat} in {year}?"
    else:
        order_direction = "DESC"
        question_format = "Who led the league in {stat} in {year}?"

    query = text(f"""
        SELECT playerID, {stat_type} FROM pitching
        WHERE yearID = :year AND {stat_type} IS NOT NULL
        ORDER BY {stat_type} {order_direction} LIMIT 4
    """)

    try:
        results = session_db.execute(query, {"year": year}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_pitcher_stat_question: {e}")
        _safe_rollback(session_db)
        return None

    if not results or len(results) < 2:
        logging.warning(f"Not enough results found for pitcher stat question with year={year}, stat_type={stat_type}")
        return None

    correct = results[0]
    correct_player_id = correct[0]
    options_data = results[:4]

    options_player_ids = [opt[0] for opt in options_data]
    name_query = text(
        "SELECT playerID, nameFirst, nameLast FROM people WHERE playerID IN :pids"
    ).bindparams(bindparam("pids", expanding=True))
    try:
        name_results = session_db.execute(name_query, {"pids": options_player_ids}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_pitcher_stat_question (name query): {e}")
        _safe_rollback(session_db)
        return None

    player_names = {}
    for row in name_results:
        player_names[row[0]] = f"{row[1]} {row[2]}"

    options = [(pid, value) for pid, value in options_data if pid in player_names]

    if len(options) < 2:
        logging.warning(
            f"Not enough valid options found for pitcher stat question with year={year}, stat_type={stat_type}")
        return None

    random.shuffle(options)

    answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
    correct_letter = [k for k, v in answer_map.items() if v == correct[0]][0]
    correct_answer_name = player_names.get(correct[0], correct[0])

    question_id_str = f"pitcher_stat_{year}_{stat_type}_{correct_player_id}"
    question_id = hash(question_id_str)

    if asked_question_ids and question_id in asked_question_ids:
        return None

    question_text = question_format.format(stat=stat_name, year=year)

    return {
        "type": "pitcher_stat",
        "question": question_text,
        "options": {k: player_names.get(v, v) for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": correct_answer_name,
        "question_id": question_id
    }


def generate_team_performance_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a trivia question about team performance (most wins) for a given year.
    """
    if asked_question_ids is None:
        asked_question_ids = []

    # Year selection based on difficulty
    if difficulty == 'easy':
        year = random.choice(range(2005, 2020))
    elif difficulty == 'medium':
        year = random.choice(range(1990, 2020))
    else:  # hard
        year = random.choice(range(1980, 2020))

    query = text("""
        SELECT team_name FROM teams
        WHERE yearID = :year
        ORDER BY team_W DESC LIMIT 4
    """)
    try:
        results = session_db.execute(query, {"year": year}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_team_performance_question: {e}")
        _safe_rollback(session_db)
        return None

    if not results or len(results) < 2:
        logging.warning(f"Not enough results found for team performance question with year={year}")
        return None

    correct_team = results[0][0]
    teams = list(results)
    random.shuffle(teams)

    team_names = {team[0]: team[0] for team in teams}

    answer_map = {chr(97 + i): team[0] for i, team in enumerate(teams)}
    correct_letter = [k for k, v in answer_map.items() if v == correct_team][0]

    question_id_str = f"team_perf_{year}_{correct_team}"
    question_id = hash(question_id_str)

    if question_id in asked_question_ids:
        return None

    stat_name = team_stat_mapping.get('team_W', 'Wins')

    return {
        "type": "team_perf",
        "question": f"Which team had the most {stat_name} in {year}?",
        "options": {k: team_names[v] for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": correct_team,
        "question_id": question_id
    }


def generate_team_stat_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a trivia question about various team statistics for a given year.
    """
    # Year selection based on difficulty
    if difficulty == 'easy':
        year = random.choice(range(2005, 2020))
    elif difficulty == 'medium':
        year = random.choice(range(1990, 2020))
    else:  # hard
        year = random.choice(range(1980, 2020))

    # Stat selection based on difficulty
    if difficulty == 'easy':
        common_stats = ['team_R', 'team_HR', 'team_H']
    elif difficulty == 'medium':
        common_stats = ['team_R', 'team_HR', 'team_H', 'team_SB', 'team_ERA']
    else:  # hard
        common_stats = ['team_R', 'team_HR', 'team_H', 'team_SB', 'team_ERA', 'team_SV', 'team_SHO', 'team_SO']

    stat_type = random.choice(common_stats)

    # Get the human-readable name
    stat_name = team_stat_mapping.get(stat_type, stat_type.replace('team_', ''))

    # For ERA, we want the LOWEST value, not highest
    if stat_type == 'team_ERA':
        order_direction = "ASC"
        question_format = "Which team had the lowest {stat} in {year}?"
    else:
        order_direction = "DESC"
        question_format = "Which team led the league in {stat} in {year}?"

    query = text(f"""
        SELECT team_name, {stat_type} FROM teams
        WHERE yearID = :year AND {stat_type} IS NOT NULL
        ORDER BY {stat_type} {order_direction} LIMIT 4
    """)

    try:
        results = session_db.execute(query, {"year": year}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_team_stat_question: {e}")
        _safe_rollback(session_db)
        return None

    if not results or len(results) < 2:
        logging.warning(f"Not enough results found for team stat question with year={year}, stat_type={stat_type}")
        return None

    correct = results[0]
    correct_team = correct[0]
    options_data = list(results[:4])

    random.shuffle(options_data)

    answer_map = {chr(97 + i): team[0] for i, team in enumerate(options_data)}
    correct_letter = [k for k, v in answer_map.items() if v == correct_team][0]

    question_id_str = f"team_stat_{year}_{stat_type}_{correct_team}"
    question_id = hash(question_id_str)

    if asked_question_ids and question_id in asked_question_ids:
        return None

    question_text = question_format.format(stat=stat_name, year=year)

    return {
        "type": "team_stat",
        "question": question_text,
        "options": {k: v for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": correct_team,
        "question_id": question_id
    }


def generate_hof_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a question about Hall of Fame inductions.
    """
    if difficulty == 'easy':
        year_range = range(1995, 2020)
    elif difficulty == 'medium':
        year_range = range(1980, 2020)
    else:  # hard
        year_range = range(1960, 2020)

    year = random.choice(list(year_range))

    query = text("""
        SELECT playerID FROM halloffame
        WHERE yearID = :year AND inducted = 'Y'
        ORDER BY RANDOM()
        LIMIT 1
    """)

    try:
        result = session_db.execute(query, {"year": year}).fetchone()

        if not result:
            logging.warning(f"No HOF inductions found for {year}")
            return None

        inducted_id = result[0]

        name_query = text("SELECT nameFirst, nameLast FROM people WHERE playerID = :pid")
        name_result = session_db.execute(name_query, {"pid": inducted_id}).fetchone()

        if not name_result:
            return None

        inducted_name = f"{name_result[0]} {name_result[1]}"

        players_query = text("""
            SELECT DISTINCT p.playerID, p.nameFirst, p.nameLast
            FROM people p
            JOIN appearances a ON p.playerID = a.playerID
            WHERE a.yearID BETWEEN :year_min AND :year_max
            AND p.playerID NOT IN (
                SELECT playerID FROM halloffame WHERE inducted = 'Y' AND yearID <= :year
            )
            ORDER BY RANDOM()
            LIMIT 3
        """)

        year_window = 10 if difficulty == 'easy' else 20

        players = session_db.execute(players_query, {
            "year_min": year - year_window,
            "year_max": year - 1,
            "year": year
        }).fetchall()

        if len(players) < 3:
            return None

        options = [
            (inducted_id, inducted_name),
            (players[0][0], f"{players[0][1]} {players[0][2]}"),
            (players[1][0], f"{players[1][1]} {players[1][2]}"),
            (players[2][0], f"{players[2][1]} {players[2][2]}")
        ]

        random.shuffle(options)

        answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
        options_map = {chr(97 + i): opt[1] for i, opt in enumerate(options)}
        correct_letter = [k for k, v in answer_map.items() if v == inducted_id][0]

        question_id_str = f"hof_{year}_{inducted_id}"
        question_id = hash(question_id_str)

        if asked_question_ids and question_id in asked_question_ids:
            return None

        return {
            "type": "hall_of_fame",
            "question": f"Which player was inducted into the Baseball Hall of Fame in {year}?",
            "options": options_map,
            "correct_letter": correct_letter,
            "correct_answer": inducted_name,
            "question_id": question_id
        }

    except Exception as e:
        logging.error(f"Database error in generate_hof_question: {e}")
        _safe_rollback(session_db)
        return None


def generate_allstar_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a question about All-Star Game appearances.
    """
    if difficulty == 'easy':
        year_range = range(2000, 2020)
    elif difficulty == 'medium':
        year_range = range(1980, 2020)
    else:  # hard
        year_range = range(1960, 2020)

    year = random.choice(list(year_range))

    question_types = []

    if difficulty == 'easy':
        question_types = ["player_in_allstar"]
    elif difficulty == 'medium':
        question_types = ["player_in_allstar", "team_most_players"]
    else:  # hard
        question_types = ["player_in_allstar", "team_most_players", "first_time_allstars"]

    question_type = random.choice(question_types)

    try:
        if question_type == "player_in_allstar":
            query = text("""
                SELECT a.playerID, p.nameFirst, p.nameLast, a.teamID
                FROM allstarfull a
                JOIN people p ON a.playerID = p.playerID
                WHERE a.yearID = :year
                ORDER BY RANDOM()
                LIMIT 1
            """)

            allstar = session_db.execute(query, {"year": year}).fetchone()

            if not allstar:
                return None

            allstar_id = allstar[0]
            allstar_name = f"{allstar[1]} {allstar[2]}"

            nonallstars_query = text("""
                SELECT DISTINCT b.playerID, p.nameFirst, p.nameLast
                FROM batting b
                JOIN people p ON b.playerID = p.playerID
                WHERE b.yearID = :year
                AND b.playerID NOT IN (
                    SELECT playerID FROM allstarfull WHERE yearID = :year
                )
                ORDER BY RANDOM()
                LIMIT 3
            """)

            nonallstars = session_db.execute(nonallstars_query, {"year": year}).fetchall()

            if len(nonallstars) < 3:
                return None

            options = [
                (allstar_id, allstar_name),
                (nonallstars[0][0], f"{nonallstars[0][1]} {nonallstars[0][2]}"),
                (nonallstars[1][0], f"{nonallstars[1][1]} {nonallstars[1][2]}"),
                (nonallstars[2][0], f"{nonallstars[2][1]} {nonallstars[2][2]}")
            ]

            random.shuffle(options)

            answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
            options_map = {chr(97 + i): opt[1] for i, opt in enumerate(options)}
            correct_letter = [k for k, v in answer_map.items() if v == allstar_id][0]

            question_id_str = f"allstar_player_{year}_{allstar_id}"
            question_id = hash(question_id_str)

            if asked_question_ids and question_id in asked_question_ids:
                return None

            return {
                "type": "allstar_player",
                "question": f"Which of these players was selected for the {year} All-Star Game?",
                "options": options_map,
                "correct_letter": correct_letter,
                "correct_answer": allstar_name,
                "question_id": question_id
            }

        elif question_type == "team_most_players":
            teams_query = text("""
                SELECT teamID, COUNT(*) as player_count
                FROM allstarfull
                WHERE yearID = :year
                GROUP BY teamID
                ORDER BY player_count DESC
                LIMIT 4
            """)

            teams = session_db.execute(teams_query, {"year": year}).fetchall()

            if len(teams) < 4:
                return None

            top_team = teams[0]

            team_ids = [team[0] for team in teams]
            team_names_query = text(
                "SELECT teamID, team_name FROM teams WHERE teamID IN :team_ids AND yearID = :year"
            ).bindparams(bindparam("team_ids", expanding=True))

            team_names = session_db.execute(team_names_query, {
                "team_ids": team_ids,
                "year": year
            }).fetchall()

            if len(team_names) < 4:
                return None

            team_name_map = {team[0]: team[1] for team in team_names}

            options = []
            for team in teams:
                team_id = team[0]
                if team_id in team_name_map:
                    options.append((team_id, team_name_map[team_id]))

            if len(options) < 4:
                return None

            random.shuffle(options)

            answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
            options_map = {chr(97 + i): opt[1] for i, opt in enumerate(options)}
            correct_letter = [k for k, v in answer_map.items() if v == top_team[0]][0]

            question_id_str = f"allstar_team_{year}_{top_team[0]}"
            question_id = hash(question_id_str)

            if asked_question_ids and question_id in asked_question_ids:
                return None

            return {
                "type": "allstar_team",
                "question": f"Which team had the most All-Stars in {year}?",
                "options": options_map,
                "correct_letter": correct_letter,
                "correct_answer": team_name_map.get(top_team[0], top_team[0]),
                "question_id": question_id
            }

    except Exception as e:
        logging.error(f"Database error in generate_allstar_question: {e}")
        _safe_rollback(session_db)
        return None


def generate_worldseries_question(session_db, asked_question_ids, difficulty='medium'):
    """
    Generates a question about World Series winners.
    """
    if difficulty == 'easy':
        year_range = range(2000, 2020)
    elif difficulty == 'medium':
        year_range = range(1980, 2020)
    else:  # hard
        year_range = range(1960, 2020)

    year = random.choice(list(year_range))

    try:
        ws_query = text("""
            SELECT teamIDwinner FROM seriespost
            WHERE yearID = :year AND round = 'WS'
            LIMIT 1
        """)

        winner = session_db.execute(ws_query, {"year": year}).fetchone()

        if not winner:
            return None

        winner_id = winner[0]

        teams_query = text("""
            SELECT teamID, team_name FROM teams
            WHERE yearID = :year
            ORDER BY RANDOM()
            LIMIT 8
        """)

        teams = session_db.execute(teams_query, {"year": year}).fetchall()

        if len(teams) < 4:
            return None

        team_name_map = {team[0]: team[1] for team in teams}

        if winner_id not in team_name_map:
            winner_name_query = text("""
                SELECT team_name FROM teams
                WHERE teamID = :team_id AND yearID = :year
                LIMIT 1
            """)

            winner_name_result = session_db.execute(winner_name_query, {
                "team_id": winner_id,
                "year": year
            }).fetchone()

            if winner_name_result:
                team_name_map[winner_id] = winner_name_result[0]
            else:
                return None

        options = [(winner_id, team_name_map[winner_id])]

        other_teams = [(team_id, name) for team_id, name in team_name_map.items() if team_id != winner_id]
        random.shuffle(other_teams)

        options.extend(other_teams[:3])

        if len(options) < 4:
            return None

        random.shuffle(options)

        answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
        options_map = {chr(97 + i): opt[1] for i, opt in enumerate(options)}
        correct_letter = [k for k, v in answer_map.items() if v == winner_id][0]

        question_id_str = f"worldseries_{year}_{winner_id}"
        question_id = hash(question_id_str)

        if asked_question_ids and question_id in asked_question_ids:
            return None

        return {
            "type": "world_series",
            "question": f"Which team won the World Series in {year}?",
            "options": options_map,
            "correct_letter": correct_letter,
            "correct_answer": team_name_map[winner_id],
            "question_id": question_id
        }

    except Exception as e:
        logging.error(f"Database error in generate_worldseries_question: {e}")
        _safe_rollback(session_db)
        return None
