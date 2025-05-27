import os

def load_env(filepath):
    with open(filepath, "r") as f:
        for line in f:
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            key, value = line.strip().split("=", 1)
            os.environ[key] = value