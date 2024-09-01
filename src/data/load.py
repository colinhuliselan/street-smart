import pickle
import json
import os
from types import SimpleNamespace


def load_geodfs():
    with open(os.path.join("data", f"rdam_gdfs.pkl"), "rb") as file:
        return pickle.load(file)


def load_locations():
    with open(os.path.join("data", "locations.json"), "r") as file:
        return json.load(file)


if __name__ == "__main__":
    """
    Inspect data.
    """
    geodfs = load_geodfs()
    gdf = geodfs[0]
    print(gdf.head(5))
