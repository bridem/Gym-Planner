import json, os, time, requests
from datetime import datetime

BASE = "https://api.hevyapp.com"

# ---------- ENV ----------

def load_api_key(user):
    with open(".env") as f:
        for line in f:
            if line.strip().startswith(user + "="):
                return line.strip().split("=")[1]
    raise Exception(f"No API key for {user}")

# ---------- API ----------

def api(key, method, path, body=None):
    r = requests.request(
        method,
        BASE + path,
        headers={"api-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=30
    )
    if not r.ok:
        print(method, path, r.status_code, r.text)
        r.raise_for_status()
    return r.json()

def write(key, method, path, body):
    while True:
        try:
            return api(key, method, path, body)
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                print("429 → sleeping 120s")
                time.sleep(120)
            else:
                raise

# ---------- LOAD ----------

def load_templates(key):
    page = 1
    out = {}

    while True:
        data = api(
            api_key,
            "GET",
            f"/v1/exercise_templates?page={page}&pageSize=50"
        )

        for ex in data.get("exercise_templates", []):
            out[ex["title"]] = ex["id"]

        if page >= data.get("page_count", 1):
            break
        page += 1

    return out

#def load_templates():
#    data = json.load(open("exercise_ids.json"))
#    return {t["title"]: t["id"] for t in data["exercise_templates"]}

def load_onerms(user):
    data = json.load(open("onerms.json"))
    out = {}
    for ex, dates in data[user].items():
        latest = max(dates.keys())
        out[ex] = dates[latest]
    return out

def load_gym():
    return json.load(open("gym_config.json"))

# ---------- ROUNDING ----------

def round_weight(name, weight, gym):
    if "Dumbbell" in name:
        return min(gym["dumbbell"]["increments"], key=lambda x: abs(x - weight/2)) * 2
    if "Smith" in name:
        bar = gym["smith"]["bar"]
        per_side = (weight - bar) / 2
        plate = min(gym["smith"]["plates"], key=lambda x: abs(x - per_side))
        return bar + plate*2
    inc = gym["default_increment"]
    return round(weight / inc) * inc

# ---------- BUILD ----------

def build_sets(ex, week, one_rms, gym):
    sets = []

    for s in week["sets"]:
        out = {"type": s["type"]}

        if "pct" in s:
            rm = one_rms[ex["key"]]
            raw = rm * s["pct"]
            out["weight_kg"] = round_weight(ex["name"], raw, gym)

        if isinstance(s["reps"], list):
            out["rep_range"] = {"start": s["reps"][0], "end": s["reps"][1]}
        else:
            out["reps"] = s["reps"]

        sets.append(out)

    # accessory override
    if "sets" in ex and "reps" in ex:
        sets = [{
            "type": "normal",
            "reps": ex["reps"][0] if isinstance(ex["reps"], list) else ex["reps"]
        } for _ in range(ex["sets"])]

    return sets

def build(plan, one_rms, templates, gym, folder_id):
    routines = []

    for week in plan["weeks"]:
        for day, exercises in plan["days"].items():
            exs = []

            for ex in exercises:
                sets = build_sets(ex, week, one_rms, gym)

                block = {
                    "exercise_template_id": templates[ex["name"]],
                    "sets": sets
                }

                if "rest_seconds" in ex:
                    block["rest_seconds"] = ex["rest_seconds"]

                exs.append(block)

            routines.append({
                "title": f"{plan['name']} — {week['name']} — {day}",
                "folder_id": folder_id,
                "exercises": exs
            })

    return routines

# ---------- UPSERT ----------

def get_folder(key, name):
    data = api(key, "GET", "/v1/routine_folders")
    for f in data["routine_folders"]:
        if f["title"] == name:
            return f["id"]
    return api(key, "POST", "/v1/routine_folders", {"routine_folder": {"title": name}})["routine_folder"]["id"]

def existing_map(key):
    out = {}
    data = api(key, "GET", "/v1/routines")
    for r in data["routines"]:
        out[(r["folder_id"], r["title"])] = r["id"]
    return out

def upsert(key, routine, existing):
    k = (routine["folder_id"], routine["title"])
    body = {"routine": routine}

    if k in existing:
        write(key, "PUT", f"/v1/routines/{existing[k]}", body)
        print("updated", routine["title"])
    else:
        write(key, "POST", "/v1/routines", body)
        print("created", routine["title"])

# ---------- MAIN ----------

def main(plan_file, user):
    key = load_api_key(user)

    plan = json.load(open(plan_file))
    one_rms = load_onerms(user)
    templates = load_templates(key)
    gym = load_gym()

    folder = get_folder(key, plan["name"])
    existing = existing_map(key)

    routines = build(plan, one_rms, templates, gym, folder)

    for r in routines:
        upsert(key, r, existing)

if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2])
