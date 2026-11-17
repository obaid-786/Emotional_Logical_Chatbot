"""Run: python -m app.eval  (inside backend container or venv)"""
import asyncio
from .classifier import classify
from .router import route

CASES = [
    {"input": "I want a refund NOW, this is garbage!",     "expect": "escalate"},
    {"input": "I will sue you if this isn't fixed",         "expect": "escalate"},
    {"input": "How long does shipping take?",               "expect": "logical"},
    {"input": "What is your return policy?",                "expect": "logical"},
    {"input": "I feel really lost and alone today",         "expect": "therapist"},
    {"input": "I'm so anxious about my order",              "expect": "therapist"},
    {"input": "Hi there!",                                  "expect": "logical"},
    {"input": "Can I cancel my subscription?",              "expect": "escalate"},
    {"input": "This product broke after one day",           "expect": "therapist"},
    {"input": "What are your support hours?",               "expect": "logical"},
]

async def main():
    correct = 0
    print(f"{'Input':55} {'Route':10} {'Expect':10} {'✓/✗'}")
    print("-" * 90)
    for case in CASES:
        analysis = await classify(case["input"])
        r = route(analysis)
        ok = r == case["expect"]
        correct += ok
        print(f"{case['input'][:53]:55} {r:10} {case['expect']:10} {'✓' if ok else '✗'}")
    print("-" * 90)
    print(f"Score: {correct}/{len(CASES)} = {correct/len(CASES)*100:.0f}%")

if __name__ == "__main__":
    asyncio.run(main())