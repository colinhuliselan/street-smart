from rapidfuzz import fuzz
import random
from types import SimpleNamespace
from __future__ import annotations

from config import CONFIG

CONSTANTS = CONFIG["constants"]


def check_finish(func):
    """
    Can be used as decorator to verify if the quizz has finished, and/or should be finished
    because there are no more questions left.
    """

    def wrapper(self, *args, **kwargs):
        if self._status == "Finished":
            raise QuizFinishedError()
        result = func(self, *args, **kwargs)
        if not self._question_tracker.remaining:
            self._finish_quiz
        return result

    return wrapper


class Quiz:

    def __init__(
        self,
        location_input: dict[str, dict[str, dict[str, str]]],
        question_type: str = "Open answer",
        location_types: list[str] = ["streets"],
        n_questions: int | None = None,
    ) -> None:
        # Static
        self._location_types: list[str] = location_types
        self._question_type: str = question_type
        self._memory: int = CONSTANTS["question_memory"]
        self._questions: dict[str:Question] = self.init_questions(
            location_input, n_questions
        )

        # Dynamic
        self._status: str = "Initialized"
        self._question_tracker: _QuestionTracker = _QuestionTracker(
            set(self._questions.keys())
        )

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_question(self) -> Question:
        return self._current_question

    @property
    def n_questions(self):
        return len(self._questions)

    @property
    def n_unanswered(self):
        return self._question_tracker.n_unanswered

    def init_questions(
        self,
        location_input: dict[str, dict[str, dict[str, str]]],
        n_questions: int | None,
    ) -> None:
        if n_questions < 1:
            raise ValueError("Number of questions need to be at least 1.")
        questions = self._generate_questions(location_input)
        if not questions:
            raise ValueError("Could not generate questions from location input.")
        sampled_questions = self._generate_question_sample(questions, n_questions)
        self._questions = {q["id"]: q for q in sampled_questions}

    def _generate_questions(
        self, location_input: dict[str, dict[str, dict[str, str]]]
    ) -> set[Question]:
        questions = set()
        for i, (type, locations) in enumerate(location_input.items()):
            if type not in self._location_types:
                continue
            all_locations = list(locations.keys())
            for j, (name, details) in enumerate(locations.items()):
                questions.add(
                    Question(
                        id=f"{i}_{j}",
                        location_name=name,
                        location_type=type,
                        question_type=self._question_type,
                        question=CONSTANTS["question_template"][type],
                        answer=name,
                        hint=details["description"],
                        all_options=all_locations,
                    )
                )
        return questions

    def _generate_question_sample(
        questions: set[Question], n_questions: int | None
    ) -> set[Question]:
        if not n_questions or n_questions >= len(questions):
            return questions
        sampled_ids = random.sample(list(questions.keys()), n_questions)
        return {questions[id] for id in sampled_ids}

    def start_quiz(self):
        self._status = "In Progress"
        self.ask_question()

    def get_question(self, id):
        return self._questions[id]

    @check_finish
    def ask_question(self):
        return self._current_question or self._ask_new_question()

    def _ask_new_question(self):
        remaining_question_ids = self._question_tracker.remaining
        if not remaining_question_ids:
            self._current_question = None
            self._status = "Finished"
            return
        if remaining_question_ids > self._skipped_question_ids:
            remaining_question_ids = remaining_question_ids - self._skipped_question_ids
        sampled_question_id = self._sample_random_question_id(remaining_question_ids)
        self._question_id_history.append(sampled_question_id)
        self._current_question = self.get_question(sampled_question_id)
        return self._current_question

    @check_finish
    def skip_question(self):
        self._skipped_question_ids.add(self._current_question.id)
        self._current_question = None
        self.update_status()

    @check_finish
    def reveal_answer_for_question(self):
        print("Revealing")
        answer = self._current_question.answer
        self._skipped_question_ids.discard(self._current_question.id)
        self._revealed_question_ids.add(self._current_question.id)
        self._current_question = None
        self.update_status()
        return answer

    @check_finish
    def check_answer(self, answer=None):
        if not self._current_question:
            raise Exception("Cannot answer without current question.")
        is_correct = self._current_question.check_answer(answer)
        if is_correct:
            self._correct_question_ids.add(self._current_question.id)
            self._skipped_question_ids.discard(self._current_question.id)
            if not self._get_remaining_question_ids():
                self._status = "Finished"
            self._current_question = None
        else:
            self._incorrect_question_ids.append(self._current_question.id)
        return is_correct

    def get_stats(self):
        return {
            "n_questions": self.get_n_questions(),
            "n_correct_answers": len(self._correct_question_ids),
            "n_first_try": len(
                [
                    q
                    for q in self._correct_question_ids
                    if q not in self._incorrect_question_ids
                ]
            ),
            "n_unanswered": self.get_n_questions_asnwered(),
        }

    def _sample_random_question_id(self, ids):
        if len(ids) == 1:
            return list(ids)[0]
        memory = self._memory
        memory = min(len(ids) - 1, self._memory, len(self._question_id_history))
        if memory > 0:
            ids -= set(self._question_id_history[-memory:])
        sampled_id = random.sample(sorted(ids), 1)[0]
        return sampled_id


class _QuestionTracker:
    """
    Only uses ids.
    """

    def __init__(self, all_question_ids=set[str]):
        # Static
        self._all: set[str] = all_question_ids

        # Dynamic
        self._current_question: Question = None
        self._history: list[str] = list()
        self._skipped: set[str] = set()
        self._revealed: set[str] = set()
        self._correct: set[str] = set()
        self._incorrect: set[str] = set()

    @property
    def n_unanswered(self):
        return len(self._unanswered)

    @property
    def n_skipped(self):
        return len(self._skipped)

    @property
    def n_revealed(self):
        return len(self._revealed)

    @property
    def n_correct(self):
        return len(self._correct)

    @property
    def n_incorrect(self):
        return len(self._incorrect)

    @property
    def remaining(self):
        return self._all - self._revealed - self._correct

    def mark_skipped(self):
        if question := self._current_question:
            self._skipped.add(question["id"])

    def mark_revealed(self):
        if question := self._current_question:
            self._revealed.add(question["id"])
        self._current_question = None

    def mark_correct(self):
        if question := self._current_question:
            self._correct.add(question["id"])
        self._current_question = None

    def mark_incorrect(self):
        if question := self._current_question:
            self._incorrect.add(question["id"])


class QuizFinishedError(Exception):
    """Exception raised when an operation is attempted on a finished quiz."""

    def __init__(
        self,
        message="Quiz is finished.",
    ):
        self.message = message
        super().__init__(self.message)


class Question:

    def __init__(self, **kwargs) -> None:
        # Static
        self._id = kwargs.get("id")
        self._location_name = kwargs.get("location_name")
        self._location_type = kwargs.get("location_type")
        self._question_type = kwargs.get("question_type")
        self._question = kwargs.get("question")
        self._answer = kwargs.get("answer")
        self._hint = kwargs.get("hint")
        self._all_options = kwargs.get("all_options")

        # Dynamic
        self._previous_options = None
        self._answer_history = []

    @property
    def id(self):
        return self._id

    @property
    def question(self):
        return self._question

    @property
    def answer(self):
        return self._answer

    @property
    def hint(self):
        return self._hint

    @property
    def all_options(self):
        return self._all_options

    def check_answer(self, answer):
        is_correct = False
        if self._question_type == "Open answer":
            sim_score = fuzz.ratio(self.answer, answer)
            is_correct = sim_score >= CONSTANTS["similarity_cutoff"]
        else:
            is_correct = self.answer == answer
        return is_correct

    def generate_options(self, number=4):
        return random.shuffle(
            random.sample(self._all_options, number - 1) + [self._answer]
        )

    def __eq__(self, other):
        return isinstance(other, Question) and self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)
