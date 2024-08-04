import streamlit as st
import folium
from streamlit_folium import st_folium
from types import SimpleNamespace

from data import LOCATIONS, GEODF
from models import Quizz


def main():
    st.title("The big Roffa quizz")
    st.text("")

    # INIT
    state = get_state()

    if not state.quizz:
        get_user_input(state)
        st.stop()

    if state.quizz.status == "Finished":
        handle_quizz_finish(state)
    question = state.quizz.ask_question()

    show_progress_bar(state.quizz)

    st.header(question.question)
    with st.expander("See hint"):
        st.write(question.hint)

    provided_answer = str
    answer_submitted = bool
    if state.question_type == "Open answer":
        provided_answer = st.text_input("Your answer")
        answer_submitted = st.button("Submit")

    if answer_submitted:
        is_correct = state.quizz.check_answer(provided_answer)
        st.text(f"Answer is {is_correct}!")

    map = create_blank_map()
    fg_dict = generate_feature_groups(LOCATIONS, GEODF)
    location = question.answer
    st_folium(
        map,
        width=800,
        height=450,
        returned_objects=[],
        feature_group_to_add=fg_dict[location],
    )

    # Create two columns
    col1, col2 = st.columns(2)
    # Place the "Skip" button in the first column
    with col1:
        st.button("Skip", on_click=state.quizz.skip_question)
    with col2:
        if st.button("Show answer"):
            handle_show_answer(state)


def get_user_input(state):
    st.session_state["question_type"] = st.selectbox(
        "Choose a quizz type", ["Open answer"], 0
    )
    st.session_state["location_types"] = st.multiselect(
        "What type of locations do you qant to quizz?", ["streets"], ["streets"]
    )
    st.session_state["n_questions"] = st.slider(
        "Number of questions", 5, len(LOCATIONS["streets"]), 5
    )
    state = get_state()  # Defaults do not retrigger
    st.write("\n\n\n")  # Add space
    if st.button("Start quizz!", on_click=start_quizz, args=[state]):
        if not validate_input(state):
            st.text("WARNING: Please supply all inputs")


def start_quizz(state):
    if not validate_input(state):
        return
    quizz = Quizz(
        locations=LOCATIONS,
        question_type=state.question_type,
        location_types=state.location_types,
        n_questions=state.n_questions,
    )
    quizz.ask_question()
    st.session_state["quizz"] = quizz
    return


def show_progress_bar(quizz):
    n_answered = quizz.get_n_questions_asnwered()
    n_questions = quizz.get_n_questions()
    st.progress(
        n_answered / float(n_questions),
        f"Questions answered: {n_answered}/{n_questions}",
    )


def validate_input(state):
    return state.question_type and state.location_types and state.n_questions


def get_state():
    state = SimpleNamespace(
        quizz=st.session_state.get("quizz"),
        question_type=st.session_state.get("question_type"),
        location_types=st.session_state.get("location_types"),
        n_questions=st.session_state.get("n_questions"),
    )
    return state


def handle_show_answer(state):
    answer = state.quizz._current_question.answer
    st.text(f"The answer is {answer}")
    st.button("Continue", on_click=state.quizz.reveal_answer)


def handle_quizz_finish(state):
    st.balloons()
    st.header("Finished!")
    stats = state.quizz.get_stats()
    st.text(f"Total questions: {stats["n_questions"]}")
    st.text(f"Correct answers: {stats["n_correct_answers"]}")
    st.text(f"Correct on first try: {stats["n_first_try"]}")
    st.text(f"Not answered: {stats["n_unanswered"]}")
    st.stop()

def generate_feature_groups(locations, _geodf):
    fg_dict = {}
    for loc in locations["streets"].keys():
        loc_gdf = _geodf[_geodf["name"] == loc]
        geo_json = folium.GeoJson(
            loc_gdf, style_function=lambda feature: {"color": "red", "weight": 5}
        )
        feature_group = folium.FeatureGroup(name=loc)
        feature_group.add_child(geo_json)
        fg_dict[loc] = feature_group
    return fg_dict


@st.cache_data
def get_street_geodf(street, _geodf):
    return _geodf[_geodf["name"] == street]


@st.cache_data
def create_blank_map():
    centre_lat = 51.9225
    centre_lon = 4.47917
    max_dist = 0.1
    return folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=13,
        tiles="cartodb voyagernolabels",
        max_bounds=True,
        min_lat=centre_lat - max_dist,
        max_lat=centre_lat + max_dist,
        min_lon=centre_lon - max_dist,
        max_lon=centre_lon + max_dist,
    )

main()
