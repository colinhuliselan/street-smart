from rapidfuzz import fuzz, process
import json
import logging
import os
import random

from config import CONFIG

CONSTANTS = CONFIG["constants"]


class Quizz:

    def __init__(
        self,
        locations,
        question_type="Open answer",
        location_types=["streets"],
        n_questions=None,
    ):
        # Static
        self._questions = {}
        self._location_types = location_types
        self._question_type = question_type
        self._memory = CONSTANTS["question_memory"]
        self.init_questions(locations, n_questions)

        # Dynamic
        self._status = "In progress"
        self._current_question = None
        self._question_id_history = list()
        self._unanswered_question_ids = set(self._questions.keys())
        self._skipped_question_ids = set()
        self._revealed_question_ids = set()
        self._correct_question_ids = set()
        self._incorrect_question_ids = list()

    @property
    def status(self):
        return self._status

    @property
    def current_question(self):
        return self._current_question

    def init_questions(self, locations, n_questions):
        questions = {}
        for i, (type, _locations) in enumerate(locations.items()):
            if type not in self._location_types:
                continue
            all_locations = list(_locations.keys())
            for j, (name, details) in enumerate(_locations.items()):
                question = CONSTANTS["question_template"][type]
                id = f"{i}_{j}"
                questions[id] = Question(
                    id=id,
                    location_name=name,
                    location_type=type,
                    question_type=self._question_type,
                    question=question,
                    answer=name,
                    hint=details["description"],
                    all_options=all_locations,
                )
        if n_questions and n_questions < len(questions):
            q_ids = random.sample(list(questions.keys()), n_questions)
            questions = {q_id: questions[q_id] for q_id in q_ids}
        self._questions = questions
        return

    def get_question(self, id):
        return self._questions[id]

    def get_n_questions(self):
        return len(self._questions)

    def get_n_questions_asnwered(self):
        return (
            len(self._questions)
            - len(self._unanswered_question_ids)
            + len(self._revealed_question_ids)
        )

    def ask_question(self):
        if self._status == "Finished":
            logging.info("No questions left.")
            return
        return self._current_question or self.ask_new_question()

    def ask_new_question(self, skipped_last=True):
        remaining_question_ids = self._get_remaining_question_ids()
        if not remaining_question_ids:
            self._current_question = None
            self._status = "Finished"
            logging.info("No questions left.")
            return
        if skipped_last and remaining_question_ids > self._skipped_question_ids:
            remaining_question_ids = remaining_question_ids - self._skipped_question_ids
        sampled_question_id = self._sample_random_question_id(remaining_question_ids)
        self._question_id_history.append(sampled_question_id)
        self._current_question = self.get_question(sampled_question_id)
        return self._current_question

    def skip_question(self):
        self._skipped_question_ids.add(self._current_question.id)
        self._current_question = None
        return

    def reveal_answer(self):
        print("Revealing")
        answer = self._current_question.answer
        self._skipped_question_ids.discard(self._current_question.id)
        self._revealed_question_ids.add(self._current_question.id)
        self._current_question = None
        print(self._get_remaining_question_ids())
        if not self._get_remaining_question_ids():
            print("Finished")
            self._status = "Finished"
        return answer

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

    def _get_remaining_question_ids(self):
        return (
            self._unanswered_question_ids
            - self._revealed_question_ids
            - self._correct_question_ids
        )


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
