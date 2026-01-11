import yaml
from pathlib import Path

def load_sops():
    sops = []
    for file in Path("sops").glob("*.yaml"):
        with open(file) as f:
            sops.append(yaml.safe_load(f))
    return sops
