import json, os, time, requests
from datetime import datetime

BASE = "https://api.hevyapp.com"

# ---------- ENV ----------

def load_api_key(user):
    with open("user_config/.env") as f:
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
            key,
            "GET",
            f"/v1/exercise_templates?page={page}&pageSize=100"
        )

        for ex in data.get("exercise_templates", []):
            title = ex.pop("title")
            out[title] = ex

        if page >= data.get("page_count", 1):
            break
        page += 1

    return out

#def load_templates():
#    data = json.load(open("exercise_ids.json"))
#    return {t["title"]: t["id"] for t in data["exercise_templates"]}

def load_onerms(user):
    data = json.load(open("user_config/onerms.json"))
    out = {}
    for ex, dates in data[user].items():
        latest = max(dates.keys())
        out[ex] = dates[latest]
    return out

def load_gym():
    return json.load(open("user_config/gym_config.json"))

# ---------- ROUNDING AND RESOLVING ----------

def resolve_implement(ex, equipment):
    if "Dumbbell" in ex["name"] or equipment == "dumbbell":
        if ex.get("single_implement", False):
            return("db_single")
        else:
            return("db_double")
    if "Smith" in ex["name"]:
        return("smith")
    if "Barbell" in ex["name"] or equipment == "barbell":
        return("barbell")

def resolve_weight(implement, raw_weight, gym):
    if implement == "db_double":
        per_hand = raw_weight / 2
        choices = gym["dumbbell"]["increments"]
        per = min(choices, key=lambda x: abs(x - per_hand))
        total = per * 2
        return total, {"type": "db_double", "per_hand": per}

    if implement == "db_single":
        choices = gym["dumbbell"]["increments"]
        total = min(choices, key=lambda x: abs(x - raw_weight))
        return total, {"type": "db_single", "total": total}

    if implement in ["smith", "barbell"]:
        bar = gym[implement]["bar"]
        plates = sorted(gym[implement]["plates"], reverse=True)

        per_side = (raw_weight - bar) / 2
        remaining = per_side
        used = []

        for p in plates:
            while remaining >= p - 1e-6:
                used.append(p)
                remaining -= p

        actual_per_side = sum(used)
        total = bar + actual_per_side * 2

        return total, {
            "type": implement,
            "per_side": actual_per_side,
            "plates": used
        }

    # fallback (machines etc.)
    inc = gym["default_increment"]
    total = round(raw_weight / inc) * inc
    return total, {"type": "stack"}

# ---------- BUILD ----------

def fmt_rest(sec):
    if not sec:
        return ""
    if sec % 60 == 0:
        return f"{sec//60} min"
    return f"{sec} sec"

def build_note(name, reps, total, raw, meta, rest, gym):
    rest_txt = fmt_rest(rest)

    if meta["type"] == "db_double":
        return f"{reps} reps @ {total}kg total ({meta['per_hand']}kg each). Rounded from {raw}kg. Rest {rest_txt}."
    if meta["type"] == "db_single":
        return f"{reps} reps @ {total}kg. Rounded from {raw}kg. Rest {rest_txt}."
    if meta["type"] in ["smith", "barbell"]:
        plate_str = " + ".join(str(p) for p in meta["plates"]) or "none"
        return (
            f"{reps} reps @ {total}kg total "
            f"(bar {gym['smith']['bar']} + {round(meta['per_side'],2)}/side). "
            f"Plates/side: {plate_str}. Rest {rest_txt}."
        )

    return f"{reps} reps @ {total}kg. Rest {rest_txt}."

def build_sets(ex, week, one_rms, gym, templates):
    sets = []
    notes = []
    main = ex.get("main", False)
    equipment = templates[ex["name"]]["equipment"]
    implement = resolve_implement(ex, equipment)

    if main: # if main lift, do weekly progression
        for s in week["sets"]:
            out = {"type": s["type"]}

            if "pct" in s:
                rm = one_rms[ex["name"]]
                raw = rm * s["pct"]
                out["weight_kg"], meta = resolve_weight(implement, raw, gym)

            if isinstance(s["reps"], list):
                out["rep_range"] = {"start": s["reps"][0], "end": s["reps"][1]}
                reps = f"{s['reps'][0]}-{s['reps'][1]}"
            else:
                out["reps"] = s["reps"]
                reps = out["reps"]

            note = build_note(ex["name"], reps, out["weight_kg"], raw, meta, s["rest_seconds"], gym)

            notes.append(note)
            sets.append(out)
    else: # it's an accessory
        sets = [{
            "type": "normal",
            "reps": ex["reps"][0] if isinstance(ex["reps"], list) else ex["reps"]
        } for _ in range(ex["sets"])]

    return sets, notes

def build(plan, one_rms, templates, gym, folder_id):
    routines = []

    for week in plan["weeks"]:
        for day, exercises in plan["days"].items():
            exs = []

            for ex in exercises:
                sets, notes = build_sets(ex, week, one_rms, gym, templates)

                block = {
                    "exercise_template_id": templates[ex["name"]]["id"],
                    "sets": sets,
                }
                if notes:
                    block["notes"] = "\n".join(notes)

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
    page = 1
    while True:
        data = api(key, "GET", f"/v1/routines?page={page}&pageSize=10")
        for r in data["routines"]:
            out[(r["folder_id"], r["title"])] = r["id"]
        if page >= data.get("page_count", 1):
            break
        page += 1
    return out

def upsert(key, routine, existing):
    k = (routine["folder_id"], routine["title"])
    body = {"routine": routine}

    if k in existing:
        body["routine"].pop("folder_id") # can't have that on PUT for some reason...
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
