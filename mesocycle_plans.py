##

warmup_10r = [{"type":"warmup","pct": 0.40,"reps": 10,"rest_seconds": 90}] * 2
weeks_10r = {
  "1RM Estimation Week": {
    "main_sets": [
      {"type":"warmup",  "pct": 0.40, "reps": 15, "rest_seconds": 90},
      {"type":"warmup",  "pct": 0.40, "reps": 12, "rest_seconds": 90},
      {"type":"normal",  "pct": 0.55, "reps": 10, "rest_seconds": 120},
      {"type":"normal",  "pct": 0.60, "reps": 10, "rest_seconds": 150},
      {"type":"failure", "pct": 0.8, "reps": (8,12), "target": 10,  "rest_seconds": 180},
    ],
    "accessory_sets": None,
  },
  "W1": {
    "main_sets": (
      warmup_10r +
      [{"type": "normal", "pct": 0.60, "reps": 10, "rest_seconds": 150}] * 5
    ),
    "accessory_sets": [{"type":"normal"}] * 3,
  },
  "W2": {
    "main_sets": (
      warmup_10r +
      [{"type": "normal", "pct": 0.65, "reps": 10, "rest_seconds": 150}] * 4
    ),
    "accessory_sets": [{"type":"normal"}] * 3,
  },
  "W3": {
    "main_sets": (
      warmup_10r +
      [{"type": "normal", "pct": 0.7, "reps": 10, "rest_seconds": 150}] * 3
    ),
    "accessory_sets": [{"type":"normal"}] * 3,
  },
  "W4": {
    "main_sets": (
      warmup_10r +
      [{"type": "normal", "pct": 0.50, "reps": 10, "rest_seconds": 120},
        {"type": "normal", "pct": 0.65, "reps": 10, "rest_seconds": 150},
        {"type": "failure", "pct": 0.74, "reps": (8, 12), "target": 10,  "rest_seconds": 180}]
    ),
    "accessory_sets": [{"type":"normal"}] * 3,
  },
  "Deload Week": {
    "main_sets": (
      warmup_10r +
      [{"type":"normal","pct":0.50, "reps": 10, "rest_seconds":150}] * 2
    ),
    "accessory_sets": [{"type":"normal"}] * 2,
  }
}