import pytest

from models import Quiz, QuizFinishedError
from data import LOCATIONS


class TestQuizz:
    """
    src.models.quizz.Quiz
    """

    def test_quizz(self):
        """
        should run through all questions as expected.
        """
        # Arrange
        n_questions = len(LOCATIONS["streets"])
        question_type = "Open answer"
        location_types = ["streets"]
        quiz = Quiz(
            location_input=LOCATIONS,
            n_questions=n_questions,
            question_type=question_type,
            location_types=location_types,
        )

        # Act
        iterations = n_questions + 10 + 10
        for i in range(iterations):
            quiz.ask_question()
            if i < 10:
                quiz.skip_question()
            elif i < 30:
                if i % 2 == 0:
                    quiz.check_answer("Wrong")
                else:
                    answer = quiz.current_question.answer
                    quiz.check_answer(answer)
            elif i < 40:
                quiz.reveal_answer()
            else:
                answer = quiz.current_question.answer
                quiz.check_answer(answer)
        statistics = quiz.get_statistics()

        # Assert
        assert quiz.status == "Finished"
        with pytest.raises(QuizFinishedError):
            quiz.ask_question()
        assert statistics["n_questions"] == n_questions
        assert statistics["n_correct_answers"] == n_questions - 10
        assert statistics["n_first_try"] == n_questions - 20
        assert statistics["n_revealed"] == 10
