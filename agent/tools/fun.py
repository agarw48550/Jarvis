import random


_JOKES = [
    "Why did the developer go broke? Because they used up all their cache.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "I changed my password to 'incorrect' so when I forget it, the computer tells me 'Your password is incorrect.'",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A SQL query walks into a bar, approaches two tables and asks: 'May I join you?'",
    "To understand what recursion is, you must first understand recursion.",
    "Knock, knock. Who's there? Race condition. Race condition who?", 
    "It works on my machine.",
]


def joke() -> str:
    return random.choice(_JOKES)


def coin() -> str:
    return random.choice(["Heads", "Tails"])


def dice(sides: int = 6) -> str:
    try:
        n = int(sides)
    except Exception:
        n = 6
    n = max(2, min(100, n))
    return str(random.randint(1, n))
