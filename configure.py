from pathlib import Path
import os
import shutil

BOOTSTRAP_FILES = [
    ("config/gym.example.yaml", "user/gym.yaml"),
    ("config/warmups.example.yaml", "user/warmups.yaml"),
    ("config/plans/example_plan.example.yaml", "user/plans/example_plan.yaml"),
    ("config/onerms.example.yaml", "user/onerms.yaml"),
    ("config/secrets.example.toml", "user/secrets.toml"),
]

os.makedirs("user/plans", exist_ok=True)

created = []

for src, dst in BOOTSTRAP_FILES:
    if not Path(dst).exists():
        shutil.copy(src, dst)
        created.append(dst)

if created:
    print("Created missing config files:")
    for f in created:
        print(" -", f)

    print (
        "\nFill in your user/ values and run gen_mesocycle.py."
    )
