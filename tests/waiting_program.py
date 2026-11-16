"""Stands in for a subscription program that waits (test_waiting.py): one question a line on
stdin, its steps as lines on stdout, the way `agy --input-format stream-json` prints them."""
import json
import sys

HOW = sys.argv[1]
print(json.dumps({"event": "init", "init": {"model": HOW}}), flush=True)
if HOW == "dies":
    sys.exit(3)
for line in sys.stdin:
    said = json.loads(line)["message"]["content"]
    print(json.dumps({"event": "step_update", "step_update": {"state": "ACTIVE"}}), flush=True)
    if HOW == "refuses":
        result = {"status": "ERROR", "response": "", "error": f"cannot do {said}"}
    else:
        result = {"status": "SUCCESS",
                  "response": json.dumps({"translation": f"{HOW}: {said}"}) + "\n"}
    print(json.dumps({"event": "result", "result": result}), flush=True)
