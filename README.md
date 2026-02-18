# Gym-Planner
Gym planner - create mesocycle plan based on desired lifts and provided weekly progressive overload

How to use?  
Define an environment variable with your Hevy API key  
e.g. on Windows: "Edit environment variables for your account" -> new: HEVY_API_KEY = key (find key on Hevy's website after logging in)  
create_plan/mesocycle_plans.py : contains details of your WEEKLY schedule in a mesocycle, e.g. your planned progressive overload  
                                 MUST be imported in workout_plan.py  
create_plan/workout_plan.py : contains details of your DAILY schedule in a week. e.g., what exercises you want to do  
                              run "python workout_plan.py" in terminal to create the plan  
create_plan/compare_plans.py : not to be run, can be imported by workout_plan to evaluate the plan in terms of muscle set volume and frequency
get_1rm.py : looks in create_plan/workout_plan.py to figure out your main lifts. Then, fetches your latest 5 exercises, and if any of them are 1rm-estimating weeks ("1RM" or "W4" in title, for the default mesocycle plan in mesocycle_plans.py), calculate 1rm based on the last, failure set of the exercise
