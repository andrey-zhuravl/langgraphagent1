import sys
from dotenv import load_dotenv

from src.langgraphagent1.agent import run_once


def main() -> int:
    load_dotenv()

    user_text = " ".join(sys.argv[1:]).strip()
    if not user_text:
        print("Usage: python -m langgraphagent1 \"hello\"")
        return 2

    out = run_once(user_text, thread_id="local-dev")
    last = out["messages"][-1]
    print(last.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
