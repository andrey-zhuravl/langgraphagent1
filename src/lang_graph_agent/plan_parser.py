import json


def plan_parse(text: str) -> list[dict[str, str]]:
    lines = (text or "").splitlines()

    buf = []
    for raw in lines:
        s = raw.strip()

        if s.startswith("PLAN:"):
            continue
        list = s.split("===", 1)
        if len(list) == 1:
            buf.append({
                "tool": "",
                "step": list[0].strip()
            })
        else:
            buf.append({
                "tool":list[1].strip().split("(")[0],
                "step":list[0].strip()
            })
    return buf