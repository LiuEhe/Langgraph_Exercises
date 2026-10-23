def answer_question(state: dict[str, str]) -> dict[str, str]:
    return {"answer": f"收到问题：{state['question']}"}


initial_state = {"question": "什么是 State？", "answer": ""}
update = answer_question(initial_state)
final_state = {**initial_state, **update}
final_state1 = {**initial_state}
final_state2 = {**update}
print(final_state)
print(final_state1)
print(final_state2)