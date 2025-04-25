from sqlalchemy import text
import random

def generate_player_stat_question(session_db):
    year = random.choice(range(1980, 2020))
    stat_type = random.choice(['b_HR', 'b_AB', 'b_RBI'])

    query = text(f"""
        SELECT playerID, {stat_type} FROM batting
        WHERE yearID = :year AND {stat_type} IS NOT NULL
        ORDER BY {stat_type} DESC LIMIT 4;
    """)
    results = session_db.execute(query, {"year": year}).fetchall()

    if len(results) < 1:  # Changed to 1, as we need at least one result for a question
        return None

    correct = results[0]
    # Ensure the correct answer is among the options. If there are fewer than 4 results,
    # all are options, and the first is correct. If there are 4 or more, we take the top 4.
    options_data = results[:4]
    if correct not in options_data: # This check might not work directly with Row objects
        options_data.append(correct)
        random.shuffle(options_data)

    player_names = {}
    options_player_ids = [opt[0] for opt in options_data]
    name_query = text("SELECT playerID, nameFirst, nameLast FROM people WHERE playerID IN :pids")
    name_results = session_db.execute(name_query, {"pids": options_player_ids}).fetchall()
    for row in name_results:
        player_names[row[0]] = f"{row[1]} {row[2]}"

    options = [(pid, value) for pid, value in options_data if pid in player_names] # Filter out if no name found

    if not options:
        return None

    random.shuffle(options)

    answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
    correct_letter = [k for k, v in answer_map.items() if v == correct[0]][0]
    correct_answer_name = player_names.get(correct[0], correct[0]) # Fallback to playerID if name not found

    question_text = f"Who had the most {stat_type} in {year}?"

    return {
        "type": "player_stat",
        "question": question_text,
        "options": {k: player_names.get(v, v) for k, v in answer_map.items()}, # Use get for safety
        "correct_letter": correct_letter,
        "correct_answer": correct_answer_name
    }

def generate_team_performance_question(session_db):
    year = random.choice(range(1980, 2020))

    query = text("""
        SELECT team_name
        FROM teams
        WHERE yearID = :year
        ORDER BY team_W DESC LIMIT 1;
    """)
    result = session_db.execute(query, {"year": year}).fetchone()

    if not result:
        return None

    teams_query = text("""
        SELECT team_name FROM teams WHERE yearID = :year ORDER BY RAND() LIMIT 3;
    """)
    teams = session_db.execute(teams_query, {"year": year}).fetchall()

    teams.append((result[0],)) # Append as a single-element tuple
    random.shuffle(teams)

    team_names = {team[0]: team[0] for team in teams}
    correct_team = result[0]

    answer_map = {chr(97 + i): team[0] for i, team in enumerate(teams)}
    correct_letter = [k for k, v in answer_map.items() if v == correct_team][0]

    question_text = f"Which team had the most wins in {year}?"

    return {
        "type": "team_perf",
        "question": question_text,
        "options": {k: team_names[v] for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": team_names[correct_team]
    }