import osmnx as ox
import os
import pickle


def run():
    graph = ox.convert.to_undirected(
        ox.graph_from_place("Rotterdam, Netherlands", network_type="drive")
    )
    with open(os.path.join("data", "rdam_graph.pkl"), "wb") as file:
        pickle.dump(graph, file)

    gdf = ox.graph_to_gdfs(graph, nodes=False)
    with open(os.path.join("data", "rdam_gdf.pkl"), "wb") as file:
        pickle.dump(gdf, file)


if __name__ == "__main__":
    run()
