from __future__ import annotations
from rapidfuzz import fuzz
import random

from config import CONFIG

CONSTANTS = CONFIG["constants"]


def check_finish(func):
    """
    Can be used as decorator to verify if the quiz has finished, and/or should be finished
    because there are no more questions left.
    """

    def wrapper(self, *args, **kwargs):
        if self._status == "Finished":
            raise QuizFinishedError()
        result = func(self, *args, **kwargs)
        if not self._question_tracker.remaining:
            self.finish_quiz()
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
        self._questions: dict = dict()
        self.init_questions(location_input, n_questions)

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
        return self._question_tracker._current_question

    @property
    def n_questions_total(self):
        return len(self._questions)

    @property
    def n_questions_remaining(self):
        return self._question_tracker.n_remaining

    @property
    def n_questions_skipped(self):
        return self._question_tracker.n_skipped

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
        sampled_questions = self._sample_from_questions(questions, n_questions)
        self._questions = {q.id: q for q in sampled_questions}

    def _generate_questions(
        self, location_input: dict[str, dict[str, dict[str, str]]]
    ) -> set[Question]:
        questions = set()
        for i, (type, locations) in enumerate(location_input.items()):
            if type not in self._location_types:
                continue
            all_locations = set(locations.keys())
            for j, (name, details) in enumerate(locations.items()):
                questions.add(
                    Question(
                        id=f"{i}_{j}",
                        location_name=name,
                        location_type=type,
                        question_type=self._question_type,
                        question_prompt=CONSTANTS["question_template"][type],
                        answer=name,
                        hint=details["description"],
                        all_options=all_locations,
                    )
                )
        return questions

    def _sample_from_questions(
        self, questions: set[Question], n_questions: int | None
    ) -> set[Question]:
        if not n_questions or n_questions >= len(questions):
            return questions
        sampled_ids = random.sample([q.id for q in questions], n_questions)
        return {q for q in questions if q.id in sampled_ids}

    def start_quiz(self) -> None:
        self._status = "In Progress"
        self.ask_question()

    def finish_quiz(self) -> None:
        self._status = "Finished"

    def get_question(self, id: str) -> None:
        return self._questions[id]

    @check_finish
    def ask_question(self) -> Question:
        return self.current_question or self._ask_new_question()

    def _ask_new_question(self) -> Question:
        """
        Ensures skipped questions, if any, are asked last.
        """
        remaining_question_ids = self._question_tracker.remaining
        if remaining_question_ids > self._question_tracker._skipped:
            remaining_question_ids = (
                remaining_question_ids - self._question_tracker._skipped
            )
        sampled_question_id = self._sample_random_question_id(remaining_question_ids)
        current_question = self.get_question(sampled_question_id)
        current_question.set_multiple_choice_options()
        self._question_tracker.update_current(current_question)
        self._question_tracker.append_history()
        return current_question

    def _sample_random_question_id(self, ids: list[str]) -> str:
        for mem in range(self._memory, 0, -1):
            ids_excl_memory = ids - set(self._question_tracker._history[-mem:])
            if ids_excl_memory:
                ids = ids_excl_memory
                break
        return random.sample(sorted(ids), 1)[0]

    @check_finish
    def skip_question(self) -> None:
        self._question_tracker.mark_skipped()
        self._question_tracker.clear_current()

    @check_finish
    def reveal_answer(self, progress_quiz: bool) -> None:
        answer = self.current_question.answer
        if not progress_quiz:
            return answer
        self._question_tracker.mark_revealed()
        self._question_tracker.clear_current()
        return answer

    @check_finish
    def check_answer(self, answer: str, progress_quiz: bool) -> bool:
        is_correct = self.current_question.check_answer(answer)
        if is_correct:
            if progress_quiz:
                self._question_tracker.mark_correct()
                self._question_tracker.clear_current()
        else:
            self._question_tracker.mark_incorrect()
        return is_correct

    def get_statistics(self) -> dict[str:int]:
        return {
            "n_questions": self.n_questions_total,
            "n_correct_answers": self._question_tracker.n_correct,
            "n_first_try": len(
                [
                    q
                    for q in self._question_tracker._correct
                    if q not in self._question_tracker._incorrect
                ]
            ),
            "n_revealed": self._question_tracker.n_revealed,
        }


class _QuestionTracker:
    """
    Only uses ids.
    """

    def __init__(self, all_question_ids=set[str]) -> None:
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
    def n_history(self) -> int:
        return len(self._history)

    @property
    def n_skipped(self) -> int:
        return len(self._skipped)

    @property
    def n_revealed(self) -> int:
        return len(self._revealed)

    @property
    def n_correct(self) -> int:
        return len(self._correct)

    @property
    def n_incorrect(self) -> int:
        return len(self._incorrect)

    @property
    def remaining(self) -> set[str]:
        return self._all - self._revealed - self._correct

    @property
    def n_remaining(self) -> int:
        return len(self.remaining)

    def clear_current(self) -> None:
        self._current_question = None

    def update_current(self, question) -> None:
        self._current_question = question

    def append_history(self) -> None:
        self._history.append(self._current_question.id)

    def mark_skipped(self) -> None:
        self._skipped.add(self._current_question.id)

    def mark_revealed(self) -> None:
        self._revealed.add(self._current_question.id)
        self._skipped.discard(self._current_question.id)

    def mark_correct(self) -> None:
        self._correct.add(self._current_question.id)

    def mark_incorrect(self) -> None:
        self._incorrect.add(self._current_question.id)


class QuizFinishedError(Exception):
    """Exception raised when an operation is attempted on a finished quiz."""

    def __init__(
        self,
        message: str = "Quiz is finished.",
    ) -> None:
        self.message = message
        super().__init__(self.message)


class Question:

    def __init__(
        self,
        id: str,
        location_name: str,
        location_type: str,
        question_type: str,
        question_prompt: str,
        answer: str,
        all_options: set[str],
        hint: str | None = None,
    ) -> None:
        # Static
        self._id: str = id
        self._location_name: str = location_name
        self._location_type: str = location_type
        self._question_type: str = question_type
        self._question_prompt: str = question_prompt
        self._answer: str = answer
        self._all_options: set = all_options
        self._hint: str = hint
        self._multiple_choice_options: list = list()

        if self._question_type == "Multiple choice":
            self.set_multiple_choice_options()

    @property
    def id(self):
        return self._id

    @property
    def question_prompt(self):
        return self._question_prompt

    @property
    def answer(self):
        return self._answer

    @property
    def hint(self):
        return self._hint

    @property
    def all_options(self):
        return self._all_options

    @property
    def multiple_choice_options(self):
        return self._multiple_choice_options

    def check_answer(self, answer):
        is_correct = False
        if self._question_type == "Open answer":
            sim_score = fuzz.ratio(self.answer, answer)
            is_correct = sim_score >= CONSTANTS["similarity_cutoff"]
        else:
            is_correct = self.answer == answer
        return is_correct

    def generate_multiple_choice_options(self, number=4):
        options = random.sample(
            sorted(self._all_options - set([self._answer])), number - 1
        ) + [self._answer]
        random.shuffle(options)
        return options

    def set_multiple_choice_options(self):
        if self._question_type != "Multiple choice":
            return
        self._multiple_choice_options = self.generate_multiple_choice_options()

    def __eq__(self, other):
        return isinstance(other, Question) and self._id == other._id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._id)
