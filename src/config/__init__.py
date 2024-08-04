import yaml
import os

with open(os.path.join("src", "config", "config.yaml"), "r") as file:
    CONFIG = yaml.safe_load(file)
