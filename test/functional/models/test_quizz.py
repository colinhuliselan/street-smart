from models import Quizz
from data import LOCATIONS


class TestQuizz:
    """
    src.models.quizz.Quizz
    """


def test_quizz():
    """
    should run through all questions without errors
    """
    # Arrange
    n_questions = len(LOCATIONS["streets"])
    question_type = "Open answer"
    location_types = ["streets"]
    quizz = Quizz(
        locations=LOCATIONS,
        n_questions=n_questions,
        question_type=question_type,
        location_types=location_types,
    )

    # Act
    answer = "wrong"
    question = quizz.ask_question()
    i = 0
    while question:
        correct = quizz.check_answer(answer)
        if correct:
            answer = "wrong"
        else:
            answer = question.answer
        print(f"{question.id}")
        question = quizz.ask_question()
        i += 1
        if i > 200:
            raise Exception("Questions are not being resolved.")
