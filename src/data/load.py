import pickle
import json
import os
from types import SimpleNamespace


def load_geodf():
    with open(os.path.join("data", f"rdam_gdfs.pkl"), "rb") as file:
        return pickle.load(file)


def load_locations():
    with open(os.path.join("data", "locations.json"), "r") as file:
        return json.load(file)


if __name__ == "__main__":
    """
    Inspect data.
    """
    with open(".\\data\\rdam_gdf.pkl", "rb") as file:
        rdam_gdf = pickle.load(file)
    print(rdam_gdf.columns)
    print(rdam_gdf.head(5))
