import random
from typing import Dict, Any


MCQ_BANK: Dict[str, list] = {
    "generic": [
        {
            "question": "Which keyword is used to define a function in Python?",
            "options": ["A. function", "B. def", "C. func", "D. define"],
            "correct_answer": "B",
            "explanation": "The 'def' keyword defines a function in Python.",
        },
        {
            "question": "Which data structure operates on a Last-In, First-Out (LIFO) basis?",
            "options": ["A. Queue", "B. Stack", "C. Array", "D. Linked List"],
            "correct_answer": "B",
            "explanation": "A stack follows the LIFO principle.",
        },
        {
            "question": "Which SQL clause is used to filter rows returned by a query?",
            "options": ["A. ORDER BY", "B. GROUP BY", "C. WHERE", "D. HAVING"],
            "correct_answer": "C",
            "explanation": "The WHERE clause filters rows before grouping or selection.",
        },
        {
            "question": "What does 'HTTP' stand for in web communication?",
            "options": ["A. HyperText Transfer Protocol", "B. High Transmission Protocol", "C. Hyperlink Text Processing", "D. Host Transfer Process"],
            "correct_answer": "A",
            "explanation": "HTTP stands for HyperText Transfer Protocol.",
        },
        {
            "question": "Which Git command records changes to the local repository with a message?",
            "options": ["A. git add", "B. git commit", "C. git push", "D. git status"],
            "correct_answer": "B",
            "explanation": "git commit saves the staged changes with a message.",
        },
        {
            "question": "Which of the following is a version control system?",
            "options": ["A. Docker", "B. Git", "C. Jenkins", "D. Kubernetes"],
            "correct_answer": "B",
            "explanation": "Git is a distributed version control system.",
        },
        {
            "question": "Which protocol is commonly used to send email?",
            "options": ["A. SMTP", "B. HTTP", "C. FTP", "D. SNMP"],
            "correct_answer": "A",
            "explanation": "SMTP (Simple Mail Transfer Protocol) is used to send email.",
        },
        {
            "question": "What does the 'else' statement do in a conditional block?",
            "options": ["A. Runs when the condition is true", "B. Runs when the condition is false", "C. Always runs first", "D. Terminates the program"],
            "correct_answer": "B",
            "explanation": "The else branch runs when the if condition is false.",
        },
    ],
    "Software Developer": [
        {
            "question": "Which time complexity describes binary search on a sorted array?",
            "options": ["A. O(n)", "B. O(log n)", "C. O(n log n)", "D. O(1)"],
            "correct_answer": "B",
            "explanation": "Binary search halves the search space each step, giving O(log n).",
        },
        {
            "question": "Which SOLID principle states that a class should have only one reason to change?",
            "options": ["A. Open/Closed", "B. Single Responsibility", "C. Liskov Substitution", "D. Dependency Inversion"],
            "correct_answer": "B",
            "explanation": "The Single Responsibility Principle means one class handles one responsibility.",
        },
        {
            "question": "Which HTTP status code indicates a resource was successfully created?",
            "options": ["A. 200", "B. 201", "C. 204", "D. 301"],
            "correct_answer": "B",
            "explanation": "201 Created is returned when a new resource is successfully created.",
        },
        {
            "question": "Which data structure is best suited for implementing a priority-based task scheduler?",
            "options": ["A. Stack", "B. Heap", "C. Queue", "D. Hash Table"],
            "correct_answer": "B",
            "explanation": "A heap (priority queue) efficiently supports extracting the highest-priority item.",
        },
        {
            "question": "In object-oriented programming, what is method overloading?",
            "options": ["A. Defining multiple methods with the same name but different parameters", "B. Replacing a parent method in a child class", "C. Calling a method on a null object", "D. Hiding a method from other classes"],
            "correct_answer": "A",
            "explanation": "Overloading defines multiple methods with the same name and different signatures.",
        },
    ],
}


WRITING_BANK: Dict[str, list] = {
    "generic": [
        {
            "question": "Explain the difference between a stack and a queue, and give a real-world example of when each is used.",
        },
        {
            "question": "Describe the steps you would take to debug a program that is returning incorrect results.",
        },
        {
            "question": "Explain what an API is and why it is important in modern software development.",
        },
        {
            "question": "Describe how a relational database stores and relates data using primary and foreign keys.",
        },
    ],
    "Software Developer": [
        {
            "question": "Explain the difference between process-based concurrency (multiprocessing) and thread-based concurrency (multithreading), including when you would choose each.",
        },
        {
            "question": "Describe the benefits and drawbacks of using a microservices architecture compared to a monolithic architecture.",
        },
        {
            "question": "Explain what a race condition is, and describe how you would prevent it in a concurrent application.",
        },
        {
            "question": "Describe how you would design a system to handle a sudden large spike in user traffic without downtime.",
        },
    ],
}


def _pick(bank: list, index: int) -> dict:
    item = bank[index % len(bank)]
    return dict(item)


def get_fallback_question(
    question_type: str,
    difficulty: str,
    role: str,
    index: int,
) -> Dict[str, Any]:
    role_key = role if role in MCQ_BANK else "generic"

    if question_type == "mcq":
        bank = MCQ_BANK.get(role_key, MCQ_BANK["generic"])
        item = _pick(bank, index)
        return {
            "question_type": "mcq",
            "question": item["question"],
            "options": item["options"],
            "correct_answer": item["correct_answer"],
            "explanation": item.get("explanation", ""),
        }

    bank = WRITING_BANK.get(role_key, WRITING_BANK["generic"])
    item = _pick(bank, index)
    return {
        "question_type": "writing",
        "question": item["question"],
        "options": None,
        "correct_answer": None,
    }
