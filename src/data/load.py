import pickle
import json
import os
from types import SimpleNamespace


def load_geodf():
    gdf = SimpleNamespace()
    for network_type in ["drive", "walk"]:
        with open(os.path.join("data", f"rdam_gdf_{network_type}.pkl"), "rb") as file:
            setattr(gdf, network_type, pickle.load(file))


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
