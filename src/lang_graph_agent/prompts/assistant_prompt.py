def get_assistant_prompt_final(general_task, current_step_str):
    return (f"""Ты — ии-агент LangGraphAgent1.
Ты выполнил задачу по плану и сделал все шаги.
Вот текст всей задачи: {general_task}
Текущий шаг: {current_step_str}

Ответь:
FINAL: <текст заключительного ответа>
""")

def get_assistant_prompt(general_task, current_step_str, full_tool):
    return (f"""Ты — ии-агент LangGraphAgent1.Ты выполняешь задачу по плану.

Текущий шаг: {current_step_str}

Выполни этот шаг, используя указанный инструмент.
Доступные инструменты: {full_tool}

ФОРМАТ ВЫЗОВА инструмента, но контент передаётся отдельно:
TOOL: {{"name":"<tool_name>"}}
TOOL_ARG=<название arg1>:
<значение arg1>
TOOL_ARG=<название arg2>:
<значение arg2>

верни TOOL/TOOL_ARG блоки
Никаких других форматов.
""")