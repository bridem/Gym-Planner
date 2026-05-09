import json, yaml, time, requests

BASE = "https://api.hevyapp.com"

# ---------- ENV ----------

def load_api_key(user):
    with open("user/secrets.toml") as f:
        for line in f:
            if line.strip().startswith(user + " = "):
                return line.strip().split(" = ")[1].replace('"','')
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

def load_onerms(user):
    with open('user/onerms.yaml', 'r') as f:
        data = yaml.safe_load(f)
    out = {}
    for ex, dates in data[user].items():
        latest = max(dates.keys())
        out[ex] = dates[latest]
    return out

def load_gym():
    with open('user/gym.yaml', 'r') as f:
        return yaml.safe_load(f)

def load_warmups():
    with open('user/warmups.yaml', 'r') as f:
        return yaml.safe_load(f)
# ---------- ROUNDING AND RESOLVING ----------

def resolve_implement(ex, templates, gym_keys):
    equipment = templates[ex["name"]]["equipment"]
    if "Dumbbell" in ex["name"] or equipment == "dumbbell":
        return("dumbbell_pair") # probably fair enough to assume it's a two-handed exercise
    if "Barbell" in ex["name"] or equipment == "barbell":
        return("barbell")
    # dynamic matching:
    for key in gym_keys:
        if key.capitalize() in ex["name"]:
            return key

    return "default_increment"

def resolve_weight(implement, raw_weight, gym):
    implement_type = gym[implement]["type"]

    if implement_type == 'one_per_hand':
        per_hand = raw_weight / 2
        choices = gym[implement]["increments"]
        per = min(choices, key=lambda x: abs(x - per_hand))
        total = per * 2
        return total, {"per_hand": per}

    if implement_type == 'single_weight':
        choices = gym[implement]["increments"]
        total = min(choices, key=lambda x: abs(x - raw_weight))
        return total, {}

    if implement_type == "loadable_bar":
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
            "per_side": actual_per_side,
            "plates": used
        }

    if implement_type == 'stack':
        inc = gym[implement]["increments"]
        total = round(raw_weight / inc) * inc
        return total, {}

    raise Exception("Invalid implement type, ", implement_type)

# ---------- BUILD ----------

def fmt_rest(sec):
    if not sec:
        return ""
    if sec % 60 == 0:
        return f"{sec//60} min"
    return f"{sec} sec"

def build_note(name, reps, total, raw, implement, meta, rest, gym):
    rest_txt = fmt_rest(rest)
    implement_type = gym[implement]["type"]

    if implement_type == "one_per_hand":
        return f"{reps} reps @ {total}kg total ({meta['per_hand']}kg each). Rounded from {raw:.1f}kg. Rest {rest_txt}."

    if implement_type == "single_weight":
        return f"{reps} reps @ {total}kg. Rounded from {raw:.1f}kg. Rest {rest_txt}."

    if implement_type == "loadable_bar":
        plate_str = " + ".join(str(p) for p in meta["plates"]) or "none"
        return (
            f"{reps} reps @ {total}kg total "
            f"(bar {gym[implement]['bar']} + {round(meta['per_side'],2)}/side). "
            f"Rounded from {raw:.1f}kg. "
            f"Plates/side: {plate_str}. Rest {rest_txt}."
        )

    return f"{reps} reps @ {total}kg. Rounded from {raw:.1f}kg. Rest {rest_txt}."

def build_warmups(warmup, ref_weight, ex, implement, gym):
    sets = warmup["sets"]

    out = []
    notes = []
    for w in sets:
        raw = ref_weight * w["pct"]
        total, meta = resolve_weight(implement, raw, gym)

        out.append({
            "type": "warmup",
            "weight_kg": total,
            "reps": w["reps"]
        })

        note = build_note(ex["name"], w["reps"], total, raw, implement, meta, w["rest_seconds"], gym)
        notes.append(note)

    return out, notes

def build_sets(ex, week, one_rms, onerm_scale, gym, templates, warmups):
    sets = []
    notes = []
    main = ex.get("main", False)
    implement = ex.get("implement", None)
    if not implement: # try guess what implement it is
        implement = resolve_implement(ex, templates, gym.keys())
    warmup_name = week.get("warmup", None)
    if warmup_name:
        warmup = warmups[warmup_name]

    if main: # if main lift, do weekly progression
        onerm = one_rms[ex["name"]]
        training_max = onerm * onerm_scale
        if warmup_name: # if warmups have been defined in plan.yaml
            if warmup["mode"] == "working_set":
                working_set = week.get("working_set", 1)
                working_pc = week["sets"][working_set-1]["pct"]
                warmup_ref_weight = training_max * working_pc
            else:
                warmup_ref_weight = training_max
            warmup_sets, warmup_notes = build_warmups(warmup, warmup_ref_weight, ex, implement, gym)
            sets.extend(warmup_sets)
            notes.extend(warmup_notes)

        for s in week["sets"]:
            out = {"type": s["type"]}

            if "pct" in s:
                raw = training_max * s["pct"]
                out["weight_kg"], meta = resolve_weight(implement, raw, gym)

            if isinstance(s["reps"], list):
                out["rep_range"] = {"start": s["reps"][0], "end": s["reps"][1]}
                reps = f"{s['reps'][0]}-{s['reps'][1]}"
            else:
                out["reps"] = s["reps"]
                reps = out["reps"]

            note = build_note(ex["name"], reps, out["weight_kg"], raw, implement, meta, s["rest_seconds"], gym)

            notes.append(note)
            sets.append(out)
    else: # it's an accessory
        sets = [{
            "type": "normal",
            "reps": ex["reps"][0] if isinstance(ex["reps"], list) else ex["reps"]
        } for _ in range(ex["sets"])]

    return sets, notes

def build(plan, one_rms, templates, gym, warmups, folder_id):
    routines = []
    onerm_scale = plan.get("onerm_scale", 1)

    for week in plan["weeks"]:
        for day, exercises in plan["days"].items():
            exs = []

            for ex in exercises:
                sets, notes = build_sets(ex, week, one_rms, onerm_scale, gym, templates, warmups)



                block = {
                    "exercise_template_id": templates[ex["name"]]["id"],
                    "sets": sets,
                }
                if notes:
                    block["notes"] = "\n".join(notes)

                # determine rest seconds. Either from exercise, or max from week!
                if "rest_seconds" in ex:
                    block["rest_seconds"] = ex["rest_seconds"]

                rest_seconds = -1
                for s in week["sets"]: # get rest time from max rest_seconds
                    rest_seconds = max(rest_seconds, s["rest_seconds"])

                if rest_seconds > 0:
                    block["rest_seconds"] = rest_seconds

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
    exercise = sys.argv[2]
    time.sleep(1)

# ---------- MAIN ----------

if __name__ == "__main__":
    import sys
    plan_file = sys.argv[1]
    user = sys.argv[2]

    key = load_api_key(user)
    with open(plan_file, 'r') as f:
        plan = yaml.safe_load(f)
    one_rms = load_onerms(user)
    templates = load_templates(key)
    gym = load_gym()
    warmups = load_warmups()

    folder = get_folder(key, plan["name"])
    existing = existing_map(key)

    routines = build(plan, one_rms, templates, gym, warmups, folder)

    for r in routines:
        upsert(key, r, existing)
