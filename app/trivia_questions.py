from sqlalchemy import text, bindparam
import random
import logging

STAT_NAMES = {
    'b_HR': 'Home Runs',
    'b_AB': 'At Bats',
    'b_RBI': 'RBIs',
}


def generate_player_stat_question(session_db, asked_question_ids):
    year = random.choice(range(1980, 2020))
    stat_type = random.choice(['b_HR', 'b_AB', 'b_RBI'])

    query = text(f"""
        SELECT playerID, {stat_type} FROM batting
        WHERE yearID = :year AND {stat_type} IS NOT NULL
        ORDER BY {stat_type} DESC LIMIT 4
    """)
    try:
        results = session_db.execute(query, {"year": year}).fetchall()
    except Exception as e:
        logging.error(f"Database error in generate_player_stat_question: {e}")
        return None

    if not results or len(results) < 4:
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
        return None

    player_names = {row[0]: f"{row[1]} {row[2]}" for row in name_results}
    options = [(pid, value) for pid, value in options_data if pid in player_names]

    if len(options) < 4:
        return None

    answer_map = {chr(97 + i): opt[0] for i, opt in enumerate(options)}
    correct_letter = [k for k, v in answer_map.items() if v == correct[0]][0]
    correct_answer_name = player_names.get(correct[0], correct[0])

    question_id_str = f"player_stat_{year}_{stat_type}_{correct_player_id}"
    question_id = hash(question_id_str)

    if question_id in asked_question_ids:
        return None

    stat_display = STAT_NAMES.get(stat_type, stat_type)
    return {
        "type": "player_stat",
        "question": f"Who had the most {stat_display} in {year}?",
        "options": {k: player_names.get(v, v) for k, v in answer_map.items()},
        "correct_letter": correct_letter,
        "correct_answer": correct_answer_name,
        "question_id": question_id
    }



def generate_team_performance_question(session_db, asked_question_ids):
    if asked_question_ids is None:
        asked_question_ids = []
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
        return None

    if not results or len(results) < 4:
        return None

    correct_team = results[0][0]
    teams = list(results)
    random.shuffle(teams)

    answer_map = {chr(97 + i): team[0] for i, team in enumerate(teams)}
    correct_letter = [k for k, v in answer_map.items() if v == correct_team][0]

    question_id_str = f"team_perf_{year}_{correct_team}"
    question_id = hash(question_id_str)

    if question_id in asked_question_ids:
        return None

    return {
        "type": "team_perf",
        "question": f"Which team had the most wins in {year}?",
        "options": answer_map,
        "correct_letter": correct_letter,
        "correct_answer": correct_team,
        "question_id": question_id
    }