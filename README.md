# Gym-Planner
Tool for doing periodisation in Hevy. e.g., follow a plan to lift a certain % of 1rm every week for a set of main lifts

*How to use?*
A Hevy Pro subscription is required to use Hevy's API. Once you have a Pro subscription, you can generate your Hevy API key in Settings -> Developer on the web app.

Once you have done that, look at the files in user_config. These are specific to you and your gym. You can open and edit them in your favourite text editor (you can even use notepad).
* secrets.toml must contain your Hevy API key, once you have generated it. Enter your name and corresponding Hevy API key here.
* onerms.json contains your estimated 1rm for each of your main lifts. If you don't know these, find out (safely)! TODO: code to automatically append to this from a Hevy exercise.
* gym_config.json contains specifics about your gym. Enter all of the dumbbells available and bar weight and weight increments on the barbell / Smith machine. You can also add your own implements if your gym has something different that you want as a main lift!

You can create your custom gym plans in the plans folder. A simplistic example is already included (plan.json), detailing a simple periodisation for bench press and squats, and accessory work in the form of push-ups and step-ups. Use this file as a reference when creating your own plan(s). NOTE: you have to spell the exercise exactly the same way as Hevy does. Search for the exercise first in the Hevy app to find out its exact spelling!

Once you have editted the user_config files and created your own plan, you must execute gen_mesocycle.py using Python. Python is a programming language available for free on all computers. Once Python is installed, execute the following command in your terminal:

python gen_mesocycle.py plans/your_plan.json your_name

Change the name of your_plan.json and your_name as appropriate.

On some operating systems you may have to run python3 instead of python in the terminal.
