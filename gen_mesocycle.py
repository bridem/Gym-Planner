# gen_mesocycle.py
import json
import os
import time
import requests
import random

BASE_URL = "https://api.hevyapp.com"
API_KEY = os.environ.get("HEVY_API_KEY")
EXERCISE_IDS_PATH = "exercise_ids.json"
SMITH_CFG = {
        "bar": 11.3,
        "step": 1.25,
        "plates": (20, 10, 5, 2.5, 1.25),
            }

# ----------------------------
# API client
# ----------------------------

def _headers():
    if not API_KEY:
        raise RuntimeError("Set HEVY_API_KEY environment variable.")
    return {"api-key": API_KEY, "Content-Type": "application/json"}

class HevyClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _url(self, path):
        return self.base_url + path

    def get(self, path, params=None):
        r = requests.get(self._url(path), headers=_headers(), params=params, timeout=30)
        if not r.ok:
            print("GET", r.status_code, self._url(path), r.text)
        r.raise_for_status()
        return r.json()

    def post(self, path, body):
        r = requests.post(self._url(path), headers=_headers(), json=body, timeout=30)
        if not r.ok:
            print("POST", r.status_code, self._url(path), r.text)
        r.raise_for_status()
        return r.json()

    def put(self, path, body):
        r = requests.put(self._url(path), headers=_headers(), json=body, timeout=30)
        if not r.ok:
            print("PUT", r.status_code, self._url(path), r.text)
        r.raise_for_status()
        return r.json()

def call_with_429_retry(do_request, max_retries=5):
    """
    do_request: a zero-arg function that performs requests.* and returns the response json.
    Retries on 429 using Retry-After header if present, otherwise exponential backoff + jitter.
    """
    backoff = 130
    for attempt in range(max_retries):
        try:
            return do_request()
        except requests.HTTPError as e:
            resp = getattr(e, "response", None)
            if resp is None or resp.status_code != 429:
                raise

            # jitter so we don't sync up with the server window edge
            wait_s = backoff + random.uniform(0.0, 0.5)
            print(f"429 rate-limited. Waiting {wait_s:.2f}s then retrying (attempt {attempt+1}/{max_retries})...")
            time.sleep(wait_s)

    raise RuntimeError("Too many 429 responses; giving up after retries.")


# ----------------------------
# Templates (exercise_ids.json)
# ----------------------------

def load_templates(json_path=EXERCISE_IDS_PATH):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_title = {}
    for t in data.get("exercise_templates"):
        title = t.get("title")
        equipment = t.get("equipment")
        implement = get_implement(title, equipment)
        
        by_title[title] = {
            "id": t.get("id"),
            "implement": implement,
            "primary_muscle_group": t.get("primary_muscle_group"),
            "secondary_muscle_groups": t.get("secondary_muscle_groups"),
        }
    return by_title

def get_implement(title, equipment=None):
    if "dumbbell" in title:
        return "dumbbell"
    if "smith machine" in title:
        return "smith"
    if "machine" in title:
        return "machine"
    if "barbell" in title:
        return "barbell"
        
    return equipment

# ----------------------------
# Folder + routine upsert (normalized)
# ----------------------------

def ensure_folder(api, title):
    page = 1
    while True:
        data = api.get("/v1/routine_folders", params={"page": page, "pageSize": 10})
        folders = data.get("routine_folders", []) or []
        for f in folders:
            if f.get("title") == title:
                return f
        if page >= (data.get("page_count") or 1):
            break
        page += 1

    created = api.post("/v1/routine_folders", {"routine_folder": {"title": title}})

    return created["routine_folder"]

def list_routines(api, page_size=10):
    page = 1
    out = []
    while True:
        data = api.get("/v1/routines", params={"page": page, "pageSize": page_size})
        rs = data.get("routines", []) or []
        out.extend(rs)
        pc = data.get("page_count")
        
        if pc is None:
            if len(rs) < page_size:
                break
        else:
            if page >= pc:
                break
        page += 1
    return out

ALL_ROUTINES_CACHE = None
def get_all_routines_cached(api):
    global ALL_ROUTINES_CACHE
    if ALL_ROUTINES_CACHE is None:
        ALL_ROUTINES_CACHE = list_routines(api)
    return ALL_ROUTINES_CACHE

def find_routine(api, folder_id, title):
    folder_id = int(folder_id)
    t = title
    for r in list_routines(api, page_size=10):
        if r.get("title") == t and int(r.get("folder_id")) == folder_id:
            return r
    return None

def sanitize_routine_write(routine, for_put=False):
    """
    Hevy write schema rejects some read-only keys (notably sets[*].index).
    Also: PUT should omit folder_id (you observed 400 otherwise).
    """
    r = dict(routine)
    if for_put:
        r.pop("folder_id", None)

    exs = []
    for ex in (r.get("exercises") or []):
        ex2 = dict(ex)
        ex2.pop("index", None)
        sets2 = []
        for s in (ex2.get("sets") or []):
            s2 = dict(s)
            s2.pop("index", None)
            sets2.append(s2)
        ex2["sets"] = sets2
        exs.append(ex2)

    r["exercises"] = exs
    return r

import hashlib
import pathlib
HASH_FILE = pathlib.Path(".routine_hashes.json")

def load_hash_cache():
    if HASH_FILE.exists():
        return json.loads(HASH_FILE.read_text())
    return {}

def save_hash_cache(cache):
    HASH_FILE.write_text(json.dumps(cache, indent=2))

def upsert_routine(api, routine, delay_s=0.06):
    title = routine.get("title")
    folder_id = routine.get("folder_id")
    if not title or folder_id is None:
        raise ValueError("routine must include 'title' and 'folder_id'.")

    existing = find_routine(api, folder_id=folder_id, title=title)

    if existing:
        rid = existing["id"]
        body = {"routine": sanitize_routine_write(routine, for_put=True)}
        
        hash_cache = load_hash_cache()
        old_hash = hash_cache.get(rid)
        new_hash = hashlib.sha256(json.dumps(body).encode("utf-8")).hexdigest()
        if old_hash != new_hash:
            res = call_with_429_retry(lambda: api.put(f"/v1/routines/{rid}", body))
            if delay_s:
                time.sleep(delay_s)
            hash_cache[rid] = new_hash
            save_hash_cache(hash_cache)
            return ("updated", res)
        else:
            return ("skipped", hash)

    body = {"routine": sanitize_routine_write(routine, for_put=False)}
    res = call_with_429_retry(lambda: api.post("/v1/routines", body))
    if delay_s:
        time.sleep(delay_s)
    return ("created", res)


# ----------------------------
# Rounding (no 15kg smith plates by default)
# ----------------------------

def _round_db_per_hand(x):
    if x <= 1:
        return 1.0
    if x < 10:
        return float(round(x))          # 1 kg steps
    return float(round(x / 2.0) * 2.0)  # 2 kg steps

def round_db_total(total):
    per_hand = _round_db_per_hand(total / 2.0)
    return 2.0 * per_hand, per_hand

def plate_breakdown(per_side, plates):
    remaining = round(per_side + 1e-9, 2)
    out = []
    for p in sorted(plates, reverse=True):
        p = float(p)
        c = int(remaining // p)
        if c:
            out += [p] * c
            remaining = round(remaining - c * p, 2)
        if remaining <= 1e-9:
            break
    return out, remaining

def fmt_plates(plates):
    if not plates:
        return "none"
    counts = {}
    for p in plates:
        counts[p] = counts.get(p, 0) + 1
    parts = []
    for p in sorted(counts.keys(), reverse=True):
        c = counts[p]
        parts.append(f"{p:g}x{c}" if c > 1 else f"{p:g}")
    return " + ".join(parts)

def round_smith_total(total, bar, step, plates):
    if total <= bar:
        return bar, 0.0, [], 0.0
    desired_side = (total - bar) / 2.0
    per_side = round(desired_side / step) * step
    total_rounded = bar + 2.0 * per_side
    plist, rem = plate_breakdown(per_side, plates)
    return total_rounded, per_side, plist, rem


# ----------------------------
# Exercise blocks
# ----------------------------

def fmt_rest(sec):
    if not sec:
        return ""
    mins = sec / 60.0
    return f"{int(mins)} min" if mins.is_integer() else f"{mins:.1f} min"

def tuple_to_rep_range(tuple):
    return {"start": tuple[0], "end": tuple[1]}
        
def round_weight_and_note(target, impl):
    if impl == "dumbbell":
        total, per_hand = round_db_total(target)
        note = f"DBs {per_hand:.0f} kg/hand or total {total:.0f} (~{target:.1f})."
        return total, note

    if impl == "smith":
        rounded_total, per_side, plates, remainder = round_smith_total(
            target,
            bar=SMITH_CFG["bar"],
            step=SMITH_CFG["step"],
            plates=SMITH_CFG["plates"],
        )
        plate_str = fmt_plates(plates)
        note = (
            f"Smith total {rounded_total:.1f} "
            f"(bar {SMITH_CFG['bar']:.1f} + {per_side:.2f}/side). "
            f"Plates/side: {plate_str}. "
            f"Rounded from {target:.1f})."
        )
        if remainder > 1e-6:
            note += f" (unmatched {remainder:.2f}kg: adjust plate set)"
        return rounded_total, note

    return None, f"Unknown implement '{impl}'."

# create workout plan!
def create_workout_plan(client, weeks, working_days, template_ids, folder_title, upload=True, verbose=True):
    folder = ensure_folder(client, folder_title)
    folder_id = folder.get("id")
    plan = {}
    for week, set_data in weeks.items():
        plan[week] = {}
        for day, exs in working_days.items():
            exercises = []
            for ex_name, data in exs.items():
                template_data = template_ids[ex_name]
                tid = template_data["id"]
                impl = template_data["implement"]
                ss_id = data.get('superset_id')
                
                if "one_rm" in data.keys(): # main lift
                    sets = []
                    note_lines = []
                    max_rest = 0
                    for set in set_data["main_sets"]:
                        pct = set["pct"]
                        reps = set["reps"]
                        set_type = set.get("type", "normal")
                        rest = set.get("rest_seconds")
                        
                        target = float(data["one_rm"])*float(pct)
                        weight_kg, round_note = round_weight_and_note(target, impl)
                        
                        s = {"type": set_type, "weight_kg": weight_kg}

                        if set_type == "failure":
                            goal = set.get("target", "")
                            line = f"AMRAP @ {int(pct*100)}% (aim {goal}). {round_note}"
                            s["rep_range"] = tuple_to_rep_range(reps)
                        else:
                            reps_i = int(reps)
                            line = f"{reps_i} reps @ {int(pct*100)}%. {round_note}"
                            s["reps"] = reps_i
                            
                        if rest:
                            line += f" Rest {fmt_rest(rest)}."
                            max_rest = max(max_rest, rest)
                        note_lines.append(line)
                        sets.append(s)

                    block = {"exercise_template_id": tid, "sets": sets, "rest_seconds": max_rest, "notes": "\n".join(note_lines)}
                    
                    if ss_id is not None:
                        block["superset_id"] = ss_id
                    
                    exercises.append(block)
                        
                else: # accessory lift
                    if set_data["accessory_sets"]: # do stuff
                        reps = data.get("reps")
                        duration_seconds = data.get("duration_seconds")
                        rest = data["rest_seconds"]
                        note = data.get("note")
                        bits = []
                        if not reps: # must be duration!
                            sets = [{"type": "normal", 
                            "duration_seconds": duration_seconds} 
                            for _ in range(len(set_data["accessory_sets"]))]
                        else:
                            sets_data = {"type": "normal"}
                            if reps[0] != reps[1]:
                                sets_data["rep_range"] = tuple_to_rep_range(reps)
                            else:
                                sets_data["reps"] = int(reps[0])
                            sets = [sets_data 
                                for _ in range(len(set_data["accessory_sets"]))]
                            bits.append(f"Target reps: {reps[0]}–{reps[1]}")
                            
                        if note:
                            bits.append(note)
                        bits.append(f"Rest {fmt_rest(rest)}.")

                        block = {"exercise_template_id": tid, "sets": sets, "rest_seconds": rest, "notes": " | ".join(bits)}
                        if ss_id is not None:
                            block["superset_id"] = ss_id
                            
                        exercises.append(block)
            
            if not exercises and verbose: # empty routine. Skip
                print(f'skipping day {day}. Empty exercise list')
            else:
                # time to upsert!
                routine = {
                    "title": f"{week} — {day}",
                    "folder_id": folder_id,
                    "notes": "Auto-generated gym routine",
                    "exercises": exercises,
                    }
                    
                if upload:
                    results = upsert_routine(client, routine)
                else:
                    results = ['skipped']
                if verbose: print(f'finished day {day}. {results[0]}')
                plan[week][day] = routine
                
        if verbose: print(f'finished week {week}.')
    return plan
        
