import osmnx as ox
import os
import pickle


def run():
    for network_type in ["drive", "walk"]:
        graph = ox.convert.to_undirected(
            ox.graph_from_place("Rotterdam, Netherlands", network_type=network_type)
        )
        with open(os.path.join("data", f"rdam_graph_{network_type}.pkl"), "wb") as file:
            pickle.dump(graph, file)

        gdf = ox.graph_to_gdfs(graph, nodes=False)
        with open(os.path.join("data", f"rdam_gdf_{network_type}.pkl"), "wb") as file:
            pickle.dump(gdf, file)


if __name__ == "__main__":
    run()
