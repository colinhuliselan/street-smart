import streamlit as st
import folium
from streamlit_folium import st_folium
from types import SimpleNamespace

from data import LOCATIONS, GEODFS
from models import Quiz


def main():
    state = get_state()
    quiz = state.quiz

    st.title("The big Roffa Quiz")

    with st.sidebar:
        display_quiz_settings(state)

    if not quiz:
        with st.container(border=True):
            st.header("Fill out settings in the sidebar to start")
    elif quiz.status == "Finished":
        display_progress(state)
        display_finish_statistics(state)
    else:
        display_progress(state)
        display_question(state)
        display_answer_input(state)


def display_quiz_settings(state):
    with st.form("Quiz settings"):
        question_type = st.selectbox("Choose a quiz type", ["Open answer"], 0)
        location_types = st.multiselect(
            "Choose locations types to quiz", ["streets"], ["streets"]
        )
        n_questions = st.slider(
            "Choose number of questions", 5, len(LOCATIONS["streets"]), 5
        )
        button_text = "Start" if not state.quiz else "Restart"
        st.form_submit_button(
            button_text,
            on_click=handle_settings_submit_click,
            args=[question_type, location_types, n_questions],
        )


def handle_settings_submit_click(question_type, location_types, n_questions):
    if not (question_type and location_types and n_questions):
        st.text("WARNING: Please supply all inputs")
        return
    st.session_state["question_type"] = question_type
    st.session_state["location_types"] = location_types
    st.session_state["n_questions"] = n_questions
    quiz = Quiz(
        location_input=LOCATIONS,
        question_type=question_type,
        location_types=location_types,
        n_questions=n_questions,
    )
    quiz.start_quiz()
    st.session_state["quiz"] = quiz


def display_finish_statistics(state):
    stats = state.quiz.get_statistics()
    st.balloons()
    st.header("Finished!")
    st.text(f'Total questions: {stats["n_questions"]}')
    st.text(f'Correct answers: {stats["n_correct_answers"]}')
    st.text(f'Correct on first try: {stats["n_first_try"]}')
    st.text(f'Revealed: {stats["n_first_try"]}')


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
        display_map(state)


def display_map(state):
    st.text(f"A map for {state.quiz.current_question.answer}")


def display_answer_input(state):
    quiz = state.quiz
    question = quiz.current_question
    awaiting_continue = state.await_continue_reason is not None

    provided_answer = None
    if state.question_type == "Open answer":
        with st.form("Open answer"):
            text_input = st.text_input("Enter your answer")
            with st.expander("See hint"):
                st.write(question.hint)
            if st.form_submit_button(
                "Submit",
                disabled=awaiting_continue,
                on_click=handle_answer_submit_click,
                args=[state, provided_answer],
            ):
                provided_answer = text_input

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
            args=[state, provided_answer],
        )
    with col_2:
        st.button(
            "Skip question",
            disabled=awaiting_continue,
            on_click=state.quiz.skip_question,
            args=[],
        )
    with col_3:
        if st.button(
            "Reveal answer",
            disabled=awaiting_continue,
            on_click=handle_reveal_answer_click,
            args=[],
        ):
            answer = quiz.reveal_answer(progress_quiz=False)
            feedback_container.warning(
                f'Spoiler warning: the correct answer is "{answer}".'
            )


def handle_answer_submit_click(state, provided_answer):
    quiz = state.quiz
    is_correct = quiz.check_answer(provided_answer, progress_quiz=False)
    if is_correct:
        st.session_state["await_continue_reason"] = "answer_submission"


def handle_reveal_answer_click():
    st.session_state["await_continue_reason"] = "answer_reveal"


def handle_continue_click(state, provided_answer):
    if state.await_continue_reason == "answer_submission":
        state.quiz.check_answer(provided_answer, progress_quiz=True)
    elif state.await_continue_reason == "answer_reveal":
        state.quiz.reveal_answer(progress_quiz=True)
    st.session_state["await_continue_reason"] = None


def get_state():
    state = SimpleNamespace(
        quiz=st.session_state.get("quiz"),
        question_type=st.session_state.get("question_type"),
        location_types=st.session_state.get("location_types"),
        n_questions=st.session_state.get("n_questions"),
        await_continue_reason=st.session_state.get("await_continue_reason"),
    )
    return state


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


main()
