"""Answer scoring: normalised string match and LLM-judge prompts."""
import re

ABSTAIN_PATTERNS = (
    "don't know", "do not know", "not mentioned", "no information", "cannot find", "can't find",
    "not provided", "unknown", "not stated", "no record", "i don't have", "i do not have",
)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split().__str__() if False else \
        " ".join(re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split())


def contains_answer(response: str, gold: str) -> bool:
    return norm(gold) in norm(response)


def is_abstention(response: str) -> bool:
    r = response.lower()
    return any(p in r for p in ABSTAIN_PATTERNS)


JUDGE_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. Answer 'yes' if the "
    "response contains the correct answer or is equivalent to it, and 'no' otherwise. If the response "
    "only contains a subset of the information required, answer 'no'.\n\n"
    "Question: {question}\nCorrect answer: {gold}\nModel response: {response}\n\n"
    "Is the model response correct? Answer yes or no only.")

JUDGE_TEMPORAL = (
    "I will give you a question, a correct answer, and a response from a model. Answer 'yes' if the "
    "response contains the correct answer. Do not penalize off-by-one errors for the number of days. "
    "If the response only contains a subset of the information required, answer 'no'.\n\n"
    "Question: {question}\nCorrect answer: {gold}\nModel response: {response}\n\n"
    "Is the model response correct? Answer yes or no only.")

JUDGE_ABSTENTION = (
    "I will give you an unanswerable question, an explanation, and a response from a model. Answer "
    "'yes' if the model correctly identifies the question as unanswerable (says the information is "
    "not available), and 'no' otherwise.\n\n"
    "Question: {question}\nExplanation: {gold}\nModel response: {response}\n\n"
    "Does the model correctly identify the question as unanswerable? Answer yes or no only.")


def judge_prompt(question, gold, response, qtype, abstention):
    tpl = JUDGE_ABSTENTION if abstention else JUDGE_TEMPORAL if "temporal" in qtype else JUDGE_TEMPLATE
    return tpl.format(question=question, gold=gold, response=response)


def parse_yes(text: str) -> bool:
    return text.strip().lower().startswith("yes")
