import streamlit as st
import folium
from streamlit_folium import st_folium
from types import SimpleNamespace

from data import LOCATIONS, GEODFS
from models import Quiz
from lib import map

STATE_VARIABLES = [
    "quiz",
    "question_type",
    "location_types",
    "n_questions",
    "await_continue_reason",
    "provided_answer",
    "open_answer",
]


def main():
    print("Rerun -------------------")
    state = get_state()

    st.title("StreetSmart Topography Quiz")

    with st.sidebar:
        display_quiz_settings(state)

    if not state.quiz:
        with st.container(border=True):
            st.header("Fill out settings in the sidebar to start")
    elif state.quiz.status == "Finished":
        display_progress(state)
        display_finish_statistics(state)
    else:
        display_progress(state)
        display_question(state)
        display_answer_input(state)


def display_quiz_settings(state):
    with st.form("Quiz settings"):
        st.selectbox(
            "Choose a quiz type",
            ["Open answer", "Multiple choice"],
            0,
            key="question_type",
        )
        st.multiselect(
            "Choose locations types to quiz",
            ["streets"],
            ["streets"],
            key="location_types",
        )
        st.slider(
            "Choose number of questions",
            5,
            len(LOCATIONS["streets"]),
            5,
            key="n_questions",
        )
        button_text = "Start" if not state.quiz else "Restart"
        st.form_submit_button(button_text, on_click=handle_settings_submit_click)


def display_finish_statistics(state):
    stats = state.quiz.get_statistics()
    st.balloons()
    st.header("Finished!")
    st.text(f'Total questions: {stats["n_questions"]}')
    st.text(f'Correct answers: {stats["n_correct_answers"]}')
    st.text(f'Correct on first try: {stats["n_first_try"]}')
    st.text(f'Revealed: {stats["n_revealed"]}')


def display_progress(state):
    quiz = state.quiz
    n_total = quiz.n_questions_total
    n_remaining = quiz.n_questions_remaining
    n_skipped = quiz.n_questions_skipped
    n_answered = n_total - n_remaining
    st.progress(
        n_answered / float(n_total),
        f"Questions answered: {n_answered}/{n_total} ({n_skipped} skipped)",
    )


def display_question(state):
    quiz = state.quiz
    question = quiz.ask_question()
    with st.container(border=True):
        st.header(question.question_prompt)
        location = question.answer
        locations = list(LOCATIONS["streets"].keys())
        map.display_map(location, locations)


def display_map(state):
    st.text(f"A map for {state.quiz.current_question.answer}")


def display_answer_input(state):
    quiz = state.quiz
    question = quiz.current_question
    question_type = state.question_type
    awaiting_continue = state.await_continue_reason is not None
    provided_answer = state.provided_answer

    if question_type == "Open answer":
        display_open_question_input(state)
    elif question_type == "Multiple choice":
        display_mc_question_input(state)
    else:
        raise ValueError(f"Cannot handle {question_type=}")

    feedback_container = st.container(border=False)

    if provided_answer:
        is_correct = quiz.check_answer(provided_answer, progress_quiz=False)
        if is_correct:
            feedback_container.success(f'Correct! The answer is "{question.answer}".')
        elif not is_correct and not awaiting_continue:
            feedback_container.error(
                f'Oops! "{provided_answer}" is not correct. Try again!'
            )

    col_1, col_2, col_3 = st.columns(3)
    with col_1:
        st.button(
            "Continue",
            disabled=not awaiting_continue,
            on_click=handle_continue_click,
            args=(state, provided_answer),
        )
    with col_2:
        st.button(
            "Skip question",
            disabled=awaiting_continue,
            on_click=handle_skip_question_click,
        )
    with col_3:
        if st.button(
            "Reveal answer",
            disabled=awaiting_continue,
            on_click=handle_reveal_answer_click,
        ):
            answer = quiz.reveal_answer(progress_quiz=False)
            feedback_container.warning(
                f'Spoiler alert! The correct answer is "{answer}".'
            )


def display_open_question_input(state: SimpleNamespace) -> None:
    provided_answer = state.provided_answer
    question = state.quiz.current_question
    awaiting_continue = state.await_continue_reason is not None
    with st.form("Open answer"):
        st.text_input("Enter your answer", provided_answer, key="open_answer")
        with st.expander("See hint"):
            st.write(question.hint)
        st.form_submit_button(
            "Submit",
            disabled=awaiting_continue,
            on_click=handle_answer_submit_click,
        )


def display_mc_question_input(state: SimpleNamespace) -> None:
    question = state.quiz.current_question
    awaiting_continue = state.await_continue_reason is not None
    with st.container(border=True):
        col1, col2 = st.columns(2)
        options = question.multiple_choice_options
        for button_index in range(len(options)):
            col = col1 if button_index + 1 <= len(options) / 2.0 else col2
            with col:
                st.button(
                    options[button_index],
                    key=f"mc_button_{button_index}",
                    disabled=awaiting_continue,
                    on_click=handle_multiple_choice_click,
                    args=[button_index],
                )


def handle_settings_submit_click():
    """
    Callback s.t. submit button can be altered to Restart.
    """
    state = get_state()
    if not (state.question_type and state.location_types and state.n_questions):
        st.text("Please supply all inputs")
        return
    quiz = Quiz(
        location_input=LOCATIONS,
        question_type=state.question_type,
        location_types=state.location_types,
        n_questions=state.n_questions,
    )
    quiz.start_quiz()
    st.session_state["quiz"] = quiz


def handle_answer_submit_click():
    """
    Callback s.t. submit button can be disabled when answer is correct.
    """
    state = get_state()
    st.session_state["provided_answer"] = state.open_answer
    quiz = state.quiz
    is_correct = quiz.check_answer(state.open_answer, progress_quiz=False)
    if is_correct:
        st.session_state["await_continue_reason"] = "answer_submission"


def handle_multiple_choice_click(button_index):
    state = get_state()
    quiz = state.quiz
    question = quiz.current_question
    mc_answer = question.multiple_choice_options[button_index]
    st.session_state["provided_answer"] = mc_answer
    is_correct = quiz.check_answer(mc_answer, progress_quiz=False)
    if is_correct:
        st.session_state["await_continue_reason"] = "answer_submission"


def handle_reveal_answer_click():
    """
    Callback s.t. we can disable question submit.
    """
    st.session_state["await_continue_reason"] = "answer_reveal"


def handle_skip_question_click():
    """
    Callback s.t. we clear provided_answer.
    """
    state = get_state()
    state.quiz.skip_question()
    st.session_state["provided_answer"] = None


def handle_continue_click(state, provided_answer):
    """
    Callback s.t. we can progress quiz before rerunning.
    """
    if state.await_continue_reason == "answer_submission":
        state.quiz.check_answer(provided_answer, progress_quiz=True)
    elif state.await_continue_reason == "answer_reveal":
        state.quiz.reveal_answer(progress_quiz=True)
    st.session_state["await_continue_reason"] = None
    st.session_state["provided_answer"] = None


def get_state() -> SimpleNamespace:
    state = SimpleNamespace()
    update_state(state)
    return state


def clear_state(state):
    for key in STATE_VARIABLES:
        setattr(state, key, None)


def update_state(state: SimpleNamespace) -> None:
    for key in STATE_VARIABLES:
        setattr(state, key, st.session_state.get(key))


@st.cache_resource
def create_feature_groups():
    feature_groups = {}
    for loc in LOCATIONS["streets"].keys():
        for geodf in GEODFS:
            loc_gdf = geodf[geodf["name"] == loc]
            if len(loc_gdf) > 0:
                geo_json = folium.GeoJson(
                    loc_gdf,
                    style_function=lambda feature: {"color": "red", "weight": 5},
                )
                feature_group = folium.FeatureGroup(name=loc)
                feature_group.add_child(geo_json)
                feature_groups[loc] = feature_group
                break  # prioritize drive
        if not feature_groups.get(loc):
            raise Exception(f"Could not generate geojson for {loc}")
    return feature_groups


@st.cache_data
def get_street_geodf(street, _geodf):
    return _geodf[_geodf["name"] == street]


@st.cache_data
def create_blank_map(centre_lat=51.9225, centre_lon=4.47917):
    max_dist = 0.1
    return folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=13,
        # tiles="cartodb voyagernolabels",
        tiles="esri worldimagery",
        max_bounds=True,
        min_lat=centre_lat - max_dist,
        max_lat=centre_lat + max_dist,
        min_lon=centre_lon - max_dist,
        max_lon=centre_lon + max_dist,
    )


main()
