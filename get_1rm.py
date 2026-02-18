import requests
import json
from datetime import datetime
import importlib.util
import os, sys

# looks at workout plan to figure out what are main lifts and what are not

BASE_URL = "https://api.hevyapp.com/v1"

def fetch_workouts():
    headers = {"api-key": API_KEY}
    response = requests.get(f"{BASE_URL}/workouts", headers=headers)
    response.raise_for_status()
    return response.json()["workouts"]


def onerm(weight, reps):
    return weight/(1.0278-0.0278*reps)


def load_existing():
    try:
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_mains(current_plan):
    spec = importlib.util.spec_from_file_location("workout", current_plan)
    foo = importlib.util.module_from_spec(spec)
    sys.modules["workout"] = foo
    spec.loader.exec_module(foo)
    working_days = foo.working_days
    
    main_lifts = []
    for day in working_days.values():
        for ex_name, ex in day.items():
            if 'one_rm' in ex.keys():
                main_lifts.append(ex_name)
                
    return main_lifts
        

def extract_1rms():
    main_lifts = get_mains(current_plan)
    workouts = fetch_workouts()
    history = load_existing()

    for workout in workouts:
        title = workout.get("title", "")

        if not ("1RM" in title or "W4" in title):
            continue

        date = workout["start_time"][:10]

        exercises = workout["exercises"]

        for exercise in exercises:
            exercise_name = exercise["title"]
            if exercise_name in history:
                if date in history[exercise_name]:
                    continue
            if exercise_name in main_lifts:
                last_set = exercise["sets"][-1]
                weight = float(last_set["weight_kg"])
                reps = int(last_set["reps"])

                one_rm = round(onerm(weight, reps), 1)

                history.setdefault(exercise_name, {})
                history[exercise_name][date] = one_rm

    save(history)


if __name__ == "__main__":
    import glob
    current_plans = glob.glob('create_plan/workout_*')
    
    for current_plan in current_plans: # should only be one...
        person = current_plan.split('.')[-2].split('_')[-1]
        api_str = "HEVY_API_KEY"
        API_KEY = os.environ.get(api_str)
        OUTPUT_FILE = f"one_rm_history.json"
        extract_1rms()
