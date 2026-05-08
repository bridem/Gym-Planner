# Gym-Planner
Tool for doing periodisation in Hevy. e.g., follow a plan to lift a certain % of 1rm every week for a set of main lifts

*How to use?*

A Hevy Pro subscription is required to use Hevy's API. Once you have a Pro subscription, you can generate your Hevy API key in Settings -> Developer on the web app.

First, you must clone or download this repository to somewhere on your computer. You can use git to clone, or just download the repo as a zip and unzip it to a location of your choosing.

Once you have downloaded the repo, you must install it using Python. Python is a programming language available for free on all computers. Once Python is installed, execute the following command in your terminal (all operating systems come with terminals) in the location of the downloaded repo:

python bootstrap.py

Once you have done that, look at the files in user/. These are specific to you and your gym. You can open and edit them in your favourite text editor (you can even use notepad).
* secrets.toml must contain your Hevy API key, once you have generated it. Enter your name and corresponding Hevy API key here.
* onerms.yaml contains your estimated 1rm for each of your main lifts. If you don't know these, find out (safely)! TODO: code to automatically append to this from a Hevy exercise.
* gym.yaml contains specifics about weights available at your gym. Enter all of the dumbbells available and bar weight / weight increments for your barbell / Smith machine. You can also add your own implements if your gym has something different that you want as a main lift!
* warmups.yaml contains templates for automatic warmup generation. These can be defined either as a percentage of your working set weight (which in turn is a percentage of your 1rm), or just as a percentage of your 1rm / training max. NOTE: if you want to warmup to a working set weight, you must specify which set is the working set in plan.yaml (which will be covered shortly)!

You can then create your custom gym plan(s) in the user/plans folder. A simplistic example is already included (example_plan.yaml), detailing a simple periodisation for bench press and squats, and accessory work in the form of push-ups and step-ups. Use this file as a reference when creating your own plan(s). NOTE: you have to spell the exercise exactly the same way as Hevy does. Search for the exercise first in the Hevy app to find out its exact spelling! Also, you must specify the implement used (only for main lifts), corresponding to an entry gym.yaml, to use the rounding feature where exactly what weights to use are written in your Hevy notes for you. Here is also where you specify what warmup from warmups.yaml you want to use on your main lifts each week. You can also scale your 1rm down with the onerm_scale factor, e.g. if following a 5/3/1 template which uses "training max", defined as 85-90% of your 1rm, as a reference weight for your lifts.

Once you have edited the user/ files and created your own plan in user/plans/, you must install pyyaml from pip to run the script:

pip install pyyaml

Finally, gen_mesocycle.py is ready to run! Execute the following command in your terminal:

python gen_mesocycle.py user/plans/your_plan.yaml your_name

Change the name of your_plan.yaml and your_name as appropriate, based on the name of the plan file in user/plans/ and your name as written in user/secrets.toml .

On some operating systems you may have to run python3 instead of python in the terminal.

From now on, you can just run python gen_mesocycle.py ... for new / updated plans.
