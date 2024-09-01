import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
from shapely.geometry import LineString
from data import LOCATIONS, GEODFS
from streamlit_js_eval import streamlit_js_eval


def display_map(location: str, locations: list) -> None:
    print(location)
    map = create_blank_map()
    feature_groups = generate_feature_groups(locations, GEODFS)
    lat, lon = calculate_average_coord(location, GEODFS)
    # folium_static(
    #     map,
    #     width=800,
    #     height=800,
    # )
    st_folium(
        map,
        width=800,
        height=800,
        center=(lat, lon),
        returned_objects=[],
        feature_group_to_add=feature_groups[location],
    )
    # if st.session_state.get("first_render", True):
    #     st.session_state["first_render"] = False
    #     print("rerunning")
    #     st.rerun()
    #     # streamlit_js_eval(js_expressions="parent.window.location.reload()")


def generate_feature_groups(locations: str, _geodfs: list) -> dict:
    feature_groups = {}
    for loc in locations:
        geo_df = filter_geodfs(loc, _geodfs)
        geo_json = folium.GeoJson(
            geo_df,
            style_function=lambda feature: {"color": "red", "weight": 5},
        )
        feature_group = folium.FeatureGroup(name=loc)
        feature_group.add_child(geo_json)
        feature_groups[loc] = feature_group
    return feature_groups


def filter_geodfs(location, _geodfs):
    for geodf in _geodfs:
        filtered_geodf = geodf[geodf["name"] == location]
        if len(filtered_geodf) > 0:

            return filtered_geodf
    raise Exception(f"Could not find coordinates for {location}.")


@st.cache_data
def create_blank_map():
    centre_lat = 51.9225
    centre_lon = 4.47917
    max_dist = 0.1
    return folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=13,
        width=800,
        height=450,
        # tiles="cartodb voyagernolabels",
        tiles="esri worldimagery",
        max_bounds=True,
        min_lat=centre_lat - max_dist,
        max_lat=centre_lat + max_dist,
        min_lon=centre_lon - max_dist,
        max_lon=centre_lon + max_dist,
    )


def calculate_average_coord(location: str, _geodfs: list) -> tuple[float]:
    geodf = filter_geodfs(location, _geodfs)

    total_latitude = 0.0
    total_longitude = 0.0
    total_points = 0
    for line in geodf["geometry"]:
        if not isinstance(line, LineString):
            continue
        coords = list(line.coords)
        for x, y in coords:
            total_longitude += x
            total_latitude += y
            total_points += 1

    if total_points == 0:
        raise Exception(f"Could not calculate average coordinates for {location}")
    return (total_latitude / total_points, total_longitude / total_points)
