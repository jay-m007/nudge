"""Hand-written beginner mistakes, each with the hint codes that would be acceptable as the
top hint. Used by the tests (every entry must be recognised) and by tools/evaluate.py (accuracy).

Format: (exercise id, what went wrong, source, accepted top codes)
"""

BUGS = [
    # --- total
    ("total", "return inside the loop", "def total(numbers):\n    result = 0\n    for n in numbers:\n        result += n\n        return result\n    return result\n", {"return_in_loop"}),
    ("total", "accumulator reset every pass", "def total(numbers):\n    for n in numbers:\n        result = 0\n        result += n\n    return result\n", {"accumulator_reset", "name_error"}),
    ("total", "prints instead of returning", "def total(numbers):\n    result = 0\n    for n in numbers:\n        result += n\n    print(result)\n", {"return_vs_print"}),
    ("total", "starts at 1", "def total(numbers):\n    result = 1\n    for n in numbers:\n        result += n\n    return result\n", {"off_by_one"}),
    ("total", "forgets to return", "def total(numbers):\n    result = 0\n    for n in numbers:\n        result += n\n", {"missing_return", "return_vs_print"}),
    ("total", "misses the last item", "def total(numbers):\n    result = 0\n    for i in range(len(numbers) - 1):\n        result += numbers[i]\n    return result\n", {"off_by_one"}),
    ("total", "typo in a variable name", "def total(numbers):\n    result = 0\n    for n in numbers:\n        reslt += n\n    return result\n", {"name_error"}),
    ("total", "wrong function name", "def totl(numbers):\n    return 0\n", {"no_function"}),
    ("total", "missing colon", "def total(numbers)\n    return 0\n", {"syntax_colon"}),
    ("total", "unclosed bracket", "def total(numbers):\n    result = (0\n    return result\n", {"brackets"}),
    ("total", "bad indentation", "def total(numbers):\nresult = 0\nreturn result\n", {"indentation"}),
    ("total", "wrong number of parameters", "def total():\n    return 0\n", {"type_error"}),
    ("total", "calls input()", "def total(numbers):\n    n = input('number? ')\n    return n\n", {"input_call"}),
    ("total", "shadows a built-in and calls it", "def total(numbers):\n    sum = 0\n    for n in numbers:\n        sum += n\n    return sum(numbers)\n", {"type_error", "shadow_builtin"}),
    # --- largest
    ("largest", "starts at 0 (fails for negatives)", "def largest(numbers):\n    if not numbers:\n        return None\n    best = 0\n    for n in numbers:\n        if n > best:\n            best = n\n    return best\n", {"edge_negative"}),
    ("largest", "no empty check", "def largest(numbers):\n    best = numbers[0]\n    for n in numbers:\n        if n > best:\n            best = n\n    return best\n", {"index_error"}),
    ("largest", "assignment instead of comparison", "def largest(numbers):\n    best = numbers[0]\n    for n in numbers:\n        if n = best:\n            best = n\n    return best\n", {"assign_vs_compare"}),
    ("largest", "returns the last item", "def largest(numbers):\n    if not numbers:\n        return None\n    for n in numbers:\n        best = n\n    return best\n", {"wrong_answer", "constant_answer"}),
    # --- count_vowels
    ("count_vowels", "ignores capital letters", "def count_vowels(text):\n    count = 0\n    for ch in text:\n        if ch in 'aeiou':\n            count += 1\n    return count\n", {"edge_uppercase", "edge_empty", "fails_on_capital_letters"}),
    ("count_vowels", "starts counting at 1", "def count_vowels(text):\n    count = 1\n    for ch in text.lower():\n        if ch in 'aeiou':\n            count += 1\n    return count\n", {"off_by_one"}),
    ("count_vowels", "colon missing on if", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch in 'aeiou'\n            count += 1\n    return count\n", {"syntax_colon"}),
    ("count_vowels", "counts consonants", "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch not in 'aeiou':\n            count += 1\n    return count\n", {"wrong_answer"}),
    # --- reverse_text
    ("reverse_text", "assigns into a string", "def reverse_text(text):\n    n = len(text)\n    for i in range(n):\n        text[i] = text[n - 1 - i]\n    return text\n", {"string_immutable"}),
    ("reverse_text", "does not reverse", "def reverse_text(text):\n    result = ''\n    for ch in text:\n        result = result + ch\n    return result\n", {"wrong_answer", "order"}),
    # --- average
    ("average", "no empty check", "def average(numbers):\n    return sum(numbers) / len(numbers)\n", {"zero_division"}),
    ("average", "whole-number division", "def average(numbers):\n    if not numbers:\n        return 0.0\n    return sum(numbers) // len(numbers)\n", {"wrong_type", "wrong_answer"}),
    # --- fizzbuzz
    ("fizzbuzz", "range stops one short", "def fizzbuzz(n):\n    result = []\n    for i in range(1, n):\n        if i % 15 == 0:\n            result.append('FizzBuzz')\n        elif i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(str(i))\n    return result\n", {"off_by_one", "incomplete_output"}),
    ("fizzbuzz", "checks 3 before 15", "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        elif i % 15 == 0:\n            result.append('FizzBuzz')\n        else:\n            result.append(str(i))\n    return result\n", {"wrong_answer"}),
    # --- is_palindrome
    ("is_palindrome", "ignores case", "def is_palindrome(text):\n    cleaned = text.replace(' ', '')\n    return cleaned == cleaned[::-1]\n", {"edge_uppercase", "edge_spaces", "fails_on_capital_letters"}),
    ("is_palindrome", "ignores spaces rule", "def is_palindrome(text):\n    cleaned = text.lower()\n    return cleaned == cleaned[::-1]\n", {"edge_spaces", "fails_on_spaces"}),
    ("is_palindrome", "returns early in loop", "def is_palindrome(text):\n    cleaned = text.replace(' ', '').lower()\n    for i in range(len(cleaned) // 2):\n        if cleaned[i] == cleaned[-1 - i]:\n            return True\n        else:\n            return False\n    return True\n", {"return_in_loop"}),
    # --- factorial
    ("factorial", "starts at 0", "def factorial(n):\n    result = 0\n    for i in range(2, n + 1):\n        result *= i\n    return result\n", {"constant_answer", "wrong_answer"}),
    ("factorial", "recursion without base case", "def factorial(n):\n    return n * factorial(n - 1)\n", {"recursion_base"}),
    # --- fibonacci
    ("fibonacci", "naive double recursion (too slow)", "def fibonacci(n):\n    if n < 2:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n", {"slow_recursion"}),
    ("fibonacci", "no base case", "def fibonacci(n):\n    return fibonacci(n - 1) + fibonacci(n - 2)\n", {"recursion_base"}),
    # --- is_prime
    ("is_prime", "treats 1 as prime", "def is_prime(n):\n    if n == 0:\n        return False\n    for i in range(2, n):\n        if n % i == 0:\n            return False\n    return True\n", {"edge_one", "edge_negative"}),
    ("is_prime", "single = in condition", "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, n):\n        if n % i = 0:\n            return False\n    return True\n", {"assign_vs_compare"}),
    ("is_prime", "no small-number check", "def is_prime(n):\n    for i in range(2, n):\n        if n % i == 0:\n            return False\n    return True\n", {"edge_one", "edge_zero", "edge_negative"}),
    # --- word_count
    ("word_count", "counts spaces", "def word_count(sentence):\n    return sentence.count(' ') + 1\n", {"edge_empty", "edge_spaces", "fails_on_empty_input", "fails_on_spaces"}),
    # --- remove_duplicates
    ("remove_duplicates", "set() loses the order", "def remove_duplicates(items):\n    return list(set(items))\n", {"order", "wrong_answer"}),
    ("remove_duplicates", "removes while looping", "def remove_duplicates(items):\n    for item in items:\n        if items.count(item) > 1:\n            items.remove(item)\n    return items\n", {"mutate_while_iterating"}),
    # --- second_largest
    ("second_largest", "sorted index fails on short lists", "def second_largest(numbers):\n    return sorted(numbers)[-2]\n", {"index_error"}),
    ("second_largest", "duplicates of the largest", "def second_largest(numbers):\n    if len(numbers) < 2:\n        return None\n    ordered = sorted(numbers)\n    return ordered[-2]\n", {"edge_duplicates", "edge_all-same", "wrong_answer"}),
    # --- char_frequency
    ("char_frequency", "reads a missing key", "def char_frequency(text):\n    counts = {}\n    for ch in text:\n        counts[ch] += 1\n    return counts\n", {"key_error"}),
    # --- digit_sum
    ("digit_sum", "no abs for negative numbers", "def digit_sum(n):\n    total = 0\n    while n > 0:\n        total += n % 10\n        n //= 10\n    return total\n", {"edge_negative"}),
    ("digit_sum", "forgets to shrink n", "def digit_sum(n):\n    n = abs(n)\n    total = 0\n    while n > 0:\n        total += n % 10\n    return total\n", {"infinite_loop"}),
    # --- two_sum
    ("two_sum", "return None inside outer loop", "def two_sum(numbers, target):\n    for i in range(len(numbers)):\n        for j in range(i + 1, len(numbers)):\n            if numbers[i] + numbers[j] == target:\n                return [i, j]\n        return None\n", {"return_in_loop"}),
    # --- merge_sorted
    ("merge_sorted", "forgets the leftovers", "def merge_sorted(a, b):\n    result = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i])\n            i += 1\n        else:\n            result.append(b[j])\n            j += 1\n    return result\n", {"off_by_one", "incomplete_output"}),
    ("merge_sorted", "sorts the caller's list", "def merge_sorted(a, b):\n    a.extend(b)\n    a.sort()\n    return a\n", {"mutated_input"}),
    # --- binary_search
    ("binary_search", "low = mid never ends", "def binary_search(items, target):\n    low, high = 0, len(items) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if items[mid] == target:\n            return mid\n        if items[mid] < target:\n            low = mid\n        else:\n            high = mid - 1\n    return -1\n", {"infinite_loop"}),
    ("binary_search", "while low < high", "def binary_search(items, target):\n    low, high = 0, len(items) - 1\n    while low < high:\n        mid = (low + high) // 2\n        if items[mid] == target:\n            return mid\n        if items[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n", {"edge_single", "edge_edge", "wrong_answer", "edge_none"}),
    # --- gcd
    ("gcd", "no base case", "def gcd(a, b):\n    return gcd(b, a % b)\n", {"recursion_base", "zero_division"}),
    # --- balanced_brackets
    ("balanced_brackets", "pops from an empty stack", "def balanced_brackets(text):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in text:\n        if ch in '([{':\n            stack.append(ch)\n        elif ch in pairs:\n            if stack.pop() != pairs[ch]:\n                return False\n    return not stack\n", {"index_error"}),
    # --- run_length_encode
    ("run_length_encode", "no empty check", "def run_length_encode(text):\n    parts = []\n    current, count = text[0], 1\n    for ch in text[1:]:\n        if ch == current:\n            count += 1\n        else:\n            parts.append(current + str(count))\n            current, count = ch, 1\n    parts.append(current + str(count))\n    return ''.join(parts)\n", {"index_error"}),
    # --- rotate_list
    ("rotate_list", "modulo of an empty list", "def rotate_list(items, k):\n    k %= len(items)\n    return items[len(items) - k:] + items[:len(items) - k]\n", {"zero_division"}),
    ("rotate_list", "rotates the caller's list", "def rotate_list(items, k):\n    for _ in range(k):\n        items.insert(0, items.pop())\n    return items\n", {"mutated_input", "index_error"}),
    # --- anagrams
    ("anagrams", "compares sets, not counts", "def anagrams(a, b):\n    return set(a.replace(' ', '').lower()) == set(b.replace(' ', '').lower())\n", {"edge_duplicates", "wrong_answer"}),
    ("anagrams", "ignores capitals", "def anagrams(a, b):\n    return sorted(a.replace(' ', '')) == sorted(b.replace(' ', ''))\n", {"edge_uppercase", "fails_on_capital_letters"}),
    # --- transpose
    ("transpose", "uses the row count for columns", "def transpose(matrix):\n    if not matrix:\n        return []\n    return [[row[c] for row in matrix] for c in range(len(matrix))]\n", {"off_by_one", "index_error"}),
    # --- collatz_steps
    ("collatz_steps", "forgets to count", "def collatz_steps(n):\n    steps = 0\n    while n != 1:\n        if n % 2 == 0:\n            n //= 2\n        else:\n            n = 3 * n + 1\n    return steps\n", {"constant_answer", "wrong_answer"}),
    # --- caesar
    ("caesar", "assigns into a string", "def caesar(text, shift):\n    for i in range(len(text)):\n        text[i] = chr(ord(text[i]) + shift)\n    return text\n", {"string_immutable"}),
]
