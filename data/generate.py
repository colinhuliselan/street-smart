import osmnx as ox
import os
import pickle
import json


def run():
    network_types = ["drive", "walk"]
    gdfs = create_and_store_gdfs(network_types)
    filter_locations(gdfs)


def create_and_store_gdfs(network_types):
    gdfs = []
    for network_type in network_types:
        graph = ox.convert.to_undirected(
            ox.graph_from_place("Rotterdam, Netherlands", network_type=network_type)
        )

        gdf = ox.graph_to_gdfs(graph, nodes=True, edges=False)
        gdfs.append(gdf)
    with open(os.path.join("data", f"rotterdam_gdfs.pkl"), "wb") as file:
        pickle.dump(gdfs, file)
    return gdfs


def filter_locations(gdfs):
    with open(os.path.join("data", "locations_raw.json"), "r") as file:
        location_input = json.load(file)
    locations_to_remove = []
    for location_type, locations in location_input.items():
        for location in locations:
            data_exists = False
            for gdf in gdfs:
                filtered_gdf = gdf[gdf["name"] == location]
                if len(filtered_gdf) > 0:
                    data_exists = True
                    break
            if not data_exists:
                locations_to_remove.append((location_type, location))

    for location_type, location in locations_to_remove:
        print(f"Removing {location}")
        del location_input[location_type][location]

    with open(os.path.join("data", "locations.json"), "w") as file:
        json.dump(location_input, file)


if __name__ == "__main__":
    run()
