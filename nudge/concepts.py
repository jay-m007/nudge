"""Level-4 hints: a small worked example of the idea, on a *different* problem
from the exercise, so it teaches the concept without handing over the answer."""

EXAMPLES: dict[str, tuple[str, str]] = {
    "syntax_colon": (
        "Every block header ends with a colon",
        "def shout(word):\n    if len(word) > 3:      # <- colon here\n        return word.upper()\n    return word",
    ),
    "assign_vs_compare": (
        "One = stores a value, two == ask a question",
        "price = 40            # store 40 in price\nif price == 40:       # ask: is price equal to 40?\n    print('cheap')",
    ),
    "brackets": (
        "Every opening bracket or quote needs its partner",
        "label = ('Total: ' + str(round(12.456, 1)))   # count the ( and ) on each line",
    ),
    "indentation": (
        "Lines inside a block are indented by the same amount",
        "def greet(name):\n    message = 'Hi ' + name   # 4 spaces: inside the function\n    return message          # same 4 spaces",
    ),
    "name_error": (
        "A name must be created before it is used, spelled the same way",
        "def area(width, height):\n    result = width * height   # created here\n    return result            # 'resutl' would be a NameError",
    ),
    "return_vs_print": (
        "print shows a value to a human; return hands it back to the caller",
        "def double(x):\n    return x * 2       # the caller gets 2*x\n\nanswer = double(4)    # answer is now 8\n# a function that only prints would leave answer as None",
    ),
    "return_in_loop": (
        "A return inside a loop ends the whole function, on the first pass",
        "def first_even(values):\n    for v in values:\n        if v % 2 == 0:\n            return v          # return only when we FOUND it\n    return None               # reached only after checking everything",
    ),
    "accumulator_reset": (
        "Set up a running value before the loop, not inside it",
        "def total_price(prices):\n    total = 0              # before the loop: starts once\n    for p in prices:\n        total += p         # grows on every pass\n    return total",
    ),
    "off_by_one": (
        "range(n) stops one before n; len(x) is one more than the last index",
        "scores = [5, 8, 9]\nfor i in range(len(scores)):      # 0, 1, 2 - every index\n    print(i, scores[i])\n# range(len(scores) - 1) would miss the last one; range(1, len(scores)) would miss the first",
    ),
    "index_error": (
        "An index must be between 0 and len(x) - 1",
        "names = ['Ana', 'Raj']\nnames[0]   # first\nnames[1]   # last\n# names[2] raises IndexError. Check len(names) first when the list may be short or empty.",
    ),
    "key_error": (
        "Ask a dictionary before you read a key that may not exist",
        "stock = {'pen': 3}\nstock.get('ink', 0)        # 0 when missing\nif 'ink' in stock:         # or check first\n    print(stock['ink'])",
    ),
    "zero_division": (
        "Guard a division when the divisor can be zero",
        "def average(values):\n    if len(values) == 0:     # nothing to divide by\n        return 0\n    return sum(values) / len(values)",
    ),
    "type_error": (
        "Operations need matching types: you can't add a number to text",
        "age = 17\nmessage = 'Age: ' + str(age)   # convert the number first\n# 'Age: ' + age raises TypeError",
    ),
    "none_attribute": (
        "None means 'nothing came back'. Something earlier forgot to return",
        "def clean(text):\n    text = text.strip()\n    return text      # without this line clean() gives None,\n                     # and clean(x).lower() fails with 'NoneType'",
    ),
    "infinite_loop": (
        "A while loop needs something inside it that changes the condition",
        "n = 10\nwhile n > 0:\n    print(n)\n    n -= 3        # without this line n never changes and the loop never ends",
    ),
    "recursion_base": (
        "A recursive function needs a case that stops, and each call must move towards it",
        "def countdown(n):\n    if n == 0:            # base case: stop here\n        return 'liftoff'\n    return countdown(n - 1)   # smaller problem each time",
    ),
    "slow_recursion": (
        "Remember answers you've already computed instead of recomputing them",
        "def paths(n, memo=None):\n    if memo is None:\n        memo = {}              # remembers finished answers\n    if n <= 1:\n        return 1\n    if n not in memo:\n        memo[n] = paths(n - 1, memo) + paths(n - 2, memo)\n    return memo[n]\n# or keep only the last two values in a loop",
    ),
    "mutate_while_iterating": (
        "Don't change a list while looping over it. Build a new one instead",
        "readings = [3, -1, 4, -5]\npositive = []\nfor r in readings:\n    if r > 0:\n        positive.append(r)    # new list, original untouched",
    ),
    "shadow_builtin": (
        "Names like list, sum, max, str, len are built in. Reusing them hides the originals",
        "values = [1, 2, 3]       # fine\n# list = [1, 2, 3]      # now list(...) no longer works in this function\n# sum = 0               # and neither does sum(...)",
    ),
    "mutable_default": (
        "A default like [] is created once and shared by every call",
        "def add_tag(tag, tags=None):\n    if tags is None:\n        tags = []          # a fresh list on each call\n    tags.append(tag)\n    return tags",
    ),
    "integer_division": (
        "/ always gives a float; // gives a whole number",
        "7 / 2    # 3.5\n7 // 2   # 3\nn = 10\nhalf = n // 2   # 5 (an int), not 5.0",
    ),
    "string_immutable": (
        "Strings can't be changed in place. Build a new string",
        "word = 'cat'\n# word[0] = 'b'   -> TypeError\nword = 'b' + word[1:]   # a new string 'bat'",
    ),
    "edge_empty": (
        "Test your idea on the smallest input: empty, one item, zero",
        "def last_item(items):\n    if not items:        # handle empty first\n        return None\n    return items[-1]",
    ),
    "order": (
        "The right items in the wrong order are still a wrong answer",
        "result = []\nfor item in [3, 1, 2]:\n    result.append(item)   # appends keep the original order\n# result.insert(0, item) would reverse it",
    ),
    "case_whitespace": (
        "Text comparison is exact: 'Hi' is not 'hi', and spaces count",
        "name = '  Ana '\nname.strip()          # 'Ana'\nname.strip().lower()  # 'ana'",
    ),
    "unused_param": (
        "A function should use its inputs, otherwise the answer can't depend on them",
        "def greet(name):\n    return 'Hello ' + name      # uses the input\n# return 'Hello world' would ignore it",
    ),
    "input_call": (
        "A function gets its data from its parameters, not from input()",
        "def shout(word):          # word arrives from the caller\n    return word.upper()   # nothing to ask the user",
    ),
    "mutated_input": (
        "Work on a copy if the caller's list must stay unchanged",
        "def with_bonus(scores):\n    result = list(scores)   # a copy\n    result.append(100)\n    return result           # original list is untouched",
    ),
    "wrong_type": (
        "The answer must have the right type: 3 (int) is not '3' (str) or 3.0 (float)",
        "int('3') + 1        # 4: convert before doing arithmetic\nstr(4)              # '4': convert when text is wanted",
    ),
    "constant_answer": (
        "If the answer never changes, the input isn't being used",
        "def double(x):\n    return x * 2     # depends on x\n# return 8 would only be right when x is 4",
    ),
    "hardcoded": (
        "Compute the answer from the input; don't write the answers in",
        "def double(x):\n    return x * 2     # works for every x, not only the ones you tried",
    ),
}
