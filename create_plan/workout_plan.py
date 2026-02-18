##

working_days = {
"Push": {
    "Bench Press (Dumbbell)": {"one_rm": 0, "note": "push it to the limit!"},
    "Overhead Press (Dumbbell)": {"one_rm": 0},
    "Triceps Dip": {"reps": (8, 12), "rest_seconds": 120},
    },
"Pull": {
    "Lat Pulldown (Cable)": {"one_rm": 0},
    "Bent Over Row (Dumbbell)": {"one_rm": 0},
    "Hammer Curl (Dumbbell)": {"reps": (8, 12), "rest_seconds": 120},
    
    "Hip Thrust (Smith Machine)": {"reps": (8, 12), "rest_seconds": 60},
    "Standing Calf Raise (Machine)": {"reps": (8, 12), "rest_seconds": 60},
    "Face Pull": {"reps": (8, 12), "rest_seconds": 60, "superset_id": 1},
    "Cable Crunch": {"reps": (8, 12), "rest_seconds": 60, "superset_id": 1},
    },
"Legs": {
    "Squat (Dumbbell)": {"one_rm": 0},
    "Deadlift (Barbell)": {"one_rm": 0},
    "Leg Press (Machine)": {"reps": (8, 12), "rest_seconds": 120, "superset_id": 1},
    "Calf Press (Machine)": {"reps": (8, 12), "rest_seconds": 120, "superset_id": 1},
    },
}

# Run
if __name__ == "__main__":
    import mesocycle_plans as mp
    mesocycle = mp.weeks_10r

    import gen_mesocycle as gm
    
    client = gm.HevyClient()
    template_ids = gm.load_templates(json_path='exercise_ids.json')
    folder_title = "Plan"
 
    gm.create_workout_plan(client, mesocycle, working_days, template_ids, folder_title)
    
    # compare plans:
    # import compare_plans as cp
    # plan = gm.create_workout_plan(client, mesocycle, working_days, template_ids, folder_title, upload=False, verbose=False)
    # vol, freq = cp.analyze_program_sets(plan["W3"], gm.load_templates()) # look at week 3 for reference
    # import json
    # print('Volume:', json.dumps(vol, indent=4))
    # print('Frequency:', json.dumps(freq, indent=4))