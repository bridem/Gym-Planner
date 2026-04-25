from collections import defaultdict

SECONDARY_WEIGHT = 0.5
COUNT_SET_TYPES = {"normal", "failure"}  # ignore warmups

def count_sets_from_mesocycle(week_block):
    sets = 0
    for s in week_block["main_sets"]:
        if s["type"] in COUNT_SET_TYPES:
            sets += 1
    return sets


def analyze_program_sets(week_of_plan, exercise_map):
    muscle_sets = defaultdict(float)
    muscle_frequency = defaultdict(int)

    by_id = {v['id']: v | {'title': k} for k, v in exercise_map.items()}

    for day, details in week_of_plan.items():
        muscles_today = set()

        for exercise in details["exercises"]:
            exercise_name = by_id[exercise['exercise_template_id']]['title']
            sets = len(exercise['sets'])
            primary = exercise_map[exercise_name]["primary_muscle_group"]
            secondaries = exercise_map[exercise_name].get("secondary_muscle_groups")

            muscle_sets[primary] += sets
            muscles_today.add(primary)

            for secondary in secondaries:
                muscle_sets[secondary] += sets * SECONDARY_WEIGHT
                muscles_today.add(secondary)

        for m in muscles_today:
            muscle_frequency[m] += 1

    return muscle_sets, muscle_frequency
    