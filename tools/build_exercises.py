"""Authoring helper: writes nudge/exercises/*.json from the definitions below.

Expected values are computed by running the reference solution, so the tests can't
disagree with it. Run:  python tools/build_exercises.py
"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "nudge" / "exercises"
EXERCISES = []


def ex(id, level, title, concepts, function, prompt, starter, solution, cases, hints, edge_hints=None, **extra):
    EXERCISES.append(dict(id=id, level=level, title=title, concepts=concepts, function=function, prompt=prompt, starter=starter, solution=solution, cases=cases, hints=hints, edge_hints=edge_hints or {}, **extra))


def C(args, tag="basic", hidden=False):
    return dict(args=args, tag=tag, hidden=hidden)


# ------------------------------------------------------------------ level 1
ex("total", 1, "Add up a list of numbers", ["loops", "accumulator"], "total",
   "Write total(numbers) that returns the sum of all the numbers in the list.\nDo not use the built-in sum().",
   "def total(numbers):\n    # add up every number in the list and return the result\n    pass\n",
   "def total(numbers):\n    result = 0\n    for n in numbers:\n        result += n\n    return result\n",
   [C([[1, 2, 3]]), C([[10]], "single"), C([[]], "empty"), C([[-5, 2, -1]], "negative"), C([[0, 0, 0]], "zero"), C([list(range(1, 101))], "large", True), C([[2.5, 2.5]], "basic", True)],
   ["Imagine adding the numbers on paper, one at a time. What do you write down, and how does it change after each number?",
    "You need a variable that remembers the running total. What should it start at before you've seen any number?",
    "Plan: create the total (start value), loop over the list adding each number to it, and after the loop return it."],
   {"empty": "The list can be empty. What is the sum of nothing? Your starting value for the total decides the answer.", "negative": "Negative numbers are just numbers: adding them should work the same way. Check you don't skip or change them."})

ex("largest", 1, "Find the largest number", ["loops", "comparison", "edge-cases"], "largest",
   "Write largest(numbers) that returns the biggest number in the list, or None if the list is empty.\nDo not use max().",
   "def largest(numbers):\n    pass\n",
   "def largest(numbers):\n    if not numbers:\n        return None\n    best = numbers[0]\n    for n in numbers:\n        if n > best:\n            best = n\n    return best\n",
   [C([[3, 9, 2]]), C([[7]], "single"), C([[]], "empty"), C([[-4, -9, -1]], "negative"), C([[5, 5, 5]], "all-same"), C([[1, 2, 3, 4, 5]], "basic", True), C([[9, 1, 2, 3]], "basic", True), C([[-1, -2, -3, -0.5]], "negative", True)],
   ["Think about how you'd find the tallest person in a line: you'd remember the tallest so far and compare each new person.",
    "You need a variable for 'the biggest so far'. What should its first value be? Be careful: 0 is not always safe.",
    "Plan: handle the empty list first, start with the first number as the best, then compare every number and replace the best when you find a bigger one."],
   {"empty": "An empty list has no biggest number. The exercise says what to return in that case; check for it before you touch numbers[0].", "negative": "If every number is negative, a starting value of 0 would beat all of them. Start from a number that is really in the list.", "all-same": "When all numbers are equal there's nothing bigger. Check that your comparison still keeps a valid answer."})

ex("count_vowels", 1, "Count the vowels", ["strings", "loops", "counting"], "count_vowels",
   "Write count_vowels(text) that returns how many vowels (a, e, i, o, u) the text contains.\nCapital letters count too.",
   "def count_vowels(text):\n    pass\n",
   "def count_vowels(text):\n    count = 0\n    for ch in text.lower():\n        if ch in 'aeiou':\n            count += 1\n    return count\n",
   [C(["hello"]), C(["rhythm"], "zero"), C([""], "empty"), C(["AEIOU"], "uppercase"), C(["Programming Is Fun"]), C(["a" * 50], "large", True), C(["Sky and Moon"], "basic", True)],
   ["A string is a sequence of characters you can walk through one by one. What do you check about each one?",
    "You need a counter that starts at 0 and goes up by 1 each time you meet a vowel. How can you ask 'is this letter one of aeiou'?",
    "Plan: counter = 0; loop over the letters; if the letter is a vowel add 1; return the counter. Think about capital letters: 'A' is not 'a'."],
   {"uppercase": "'A' and 'a' are different characters to Python. Make the comparison ignore the difference, for example by converting the text first.", "zero": "If there are no vowels the answer is 0, not None. Make sure the counter starts at 0 and is returned either way.", "empty": "An empty text has no vowels, so the answer is 0. Make sure your code still returns something."})

ex("reverse_text", 1, "Reverse a text", ["strings", "indexing", "loops"], "reverse_text",
   "Write reverse_text(text) that returns the text backwards.\nTry to do it with a loop first (slicing tricks like text[::-1] are allowed, but you learn more with the loop).",
   "def reverse_text(text):\n    pass\n",
   "def reverse_text(text):\n    result = ''\n    for ch in text:\n        result = ch + result\n    return result\n",
   [C(["hello"]), C([""], "empty"), C(["a"], "single"), C(["Hello World"]), C(["madam"], "basic"), C(["ab" * 20], "large", True), C(["  hi "], "spaces", True)],
   ["Read the word 'stop' backwards by hand: which letter do you write first, and which last?",
    "Strings can't be changed in place, so build a new one. Each letter you meet should go... where in the new string?",
    "Plan: start with an empty result; for each letter of the original, put it in front of the result; return the result."],
   {"empty": "The reverse of an empty text is an empty text. Make sure the function still returns '' and doesn't return None.", "spaces": "Spaces are characters like any other; they must stay and move too."})

ex("fizzbuzz", 1, "FizzBuzz", ["loops", "conditionals", "modulo"], "fizzbuzz",
   "Write fizzbuzz(n) that returns a list for the numbers 1 to n. For each number: 'FizzBuzz' if it is divisible by 3 and by 5, 'Fizz' if only by 3, 'Buzz' if only by 5, otherwise the number as text, e.g. '7'.",
   "def fizzbuzz(n):\n    pass\n",
   "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            result.append('FizzBuzz')\n        elif i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(str(i))\n    return result\n",
   [C([5]), C([15]), C([1], "single"), C([0], "zero"), C([3], "basic"), C([30], "large", True), C([16], "basic", True)],
   ["Take the numbers 1 to 15 and write down by hand what each should become. Which number is the trickiest?",
    "A number divisible by both 3 and 5 also matches the 'only 3' test. Does the order of your checks matter?",
    "Plan: loop i from 1 to n inclusive; check the 'both' case first, then 3, then 5, else the number as text; collect the results in a list and return it."],
   {"zero": "n = 0 means no numbers at all, so the list is empty.", "single": "For n = 1 the list has one item and it is the text '1', not the number 1."})

ex("average", 1, "Average of a list", ["loops", "division", "edge-cases"], "average",
   "Write average(numbers) that returns the mean of the numbers as a float, or 0.0 if the list is empty.",
   "def average(numbers):\n    pass\n",
   "def average(numbers):\n    if not numbers:\n        return 0.0\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)\n",
   [C([[2, 4, 6]]), C([[5]], "single"), C([[]], "empty"), C([[1, 2]], "basic"), C([[-3, 3]], "negative"), C([[10, 20, 30, 40]], "basic", True), C([[0.5, 1.5]], "basic", True)],
   ["The average is the total divided by how many numbers there are. What two things do you need?",
    "You can get 'how many' with len(). What happens in Python if you divide by zero? When could that happen here?",
    "Plan: if the list is empty return 0.0; otherwise add everything up and divide by len(numbers)."],
   {"empty": "With no numbers there is nothing to divide by. The exercise tells you what to return; check for the empty list before dividing."},
   approx=True)

# ------------------------------------------------------------------ level 2
ex("is_palindrome", 2, "Is it a palindrome?", ["strings", "indexing", "loops"], "is_palindrome",
   "Write is_palindrome(text) that returns True if the text reads the same forwards and backwards, ignoring capital letters and spaces, otherwise False.\nExample: 'Never odd or even' is a palindrome.",
   "def is_palindrome(text):\n    pass\n",
   "def is_palindrome(text):\n    cleaned = text.replace(' ', '').lower()\n    left, right = 0, len(cleaned) - 1\n    while left < right:\n        if cleaned[left] != cleaned[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\n",
   [C(["madam"]), C(["hello"]), C([""], "empty"), C(["a"], "single"), C(["Never odd or even"], "spaces"), C(["Racecar"], "uppercase"), C(["ab"], "basic"), C(["Was it a car or a cat I saw".replace(" ", "  ")], "spaces", True), C(["abcba"], "basic", True), C(["abca"], "basic"), C(["abcdba"], "basic", True), C(["aabca"], "basic", True)],
   ["Compare the first letter with the last, the second with the second last, and so on. When can you stop?",
    "First make the text easy to compare: what should happen to capital letters and spaces before you compare anything?",
    "Plan: clean the text (lower case, no spaces); then either compare it with its reverse, or walk two positions inwards from both ends and return False at the first mismatch."],
   {"uppercase": "'R' and 'r' differ for Python. Convert the case before comparing.", "spaces": "Spaces must be ignored, so remove them first, otherwise the letters won't line up.", "empty": "An empty text reads the same both ways, so the answer is True."})

ex("factorial", 2, "Factorial", ["loops", "recursion", "edge-cases"], "factorial",
   "Write factorial(n) that returns n! = 1 x 2 x 3 x ... x n for n >= 0. By definition 0! is 1.",
   "def factorial(n):\n    pass\n",
   "def factorial(n):\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result\n",
   [C([5]), C([1], "single"), C([0], "zero"), C([3]), C([10], "large"), C([20], "large", True), C([2], "basic", True)],
   ["Work out 4! by hand: 4 x 3 x 2 x 1. What do you multiply, in what order, and what do you start from?",
    "A product that starts at 0 stays 0 forever. What should the starting value be so that multiplying works?",
    "Plan (loop): result = 1; for each number from 2 up to n multiply result by it; return result. Plan (recursion): n! = n x (n-1)!, and 0! = 1 stops the recursion."],
   {"zero": "0! is defined as 1. Make sure your code returns 1 for n = 0, not 0 and not an error.", "single": "1! is 1."})

ex("fibonacci", 2, "Fibonacci number", ["loops", "recursion", "sequences"], "fibonacci",
   "Write fibonacci(n) that returns the n-th Fibonacci number, where fibonacci(0) = 0, fibonacci(1) = 1, and every later number is the sum of the two before it: 0, 1, 1, 2, 3, 5, 8, ...",
   "def fibonacci(n):\n    pass\n",
   "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
   [C([6]), C([0], "zero"), C([1], "single"), C([2]), C([10]), C([30], "large", True), C([25], "large", True), C([37], "large", True)],
   ["Write out the first 10 numbers by hand and look at how each is made from the earlier ones.",
    "To make the next number you only need to remember the last two. How can you update both as you go round a loop?",
    "Plan: keep two variables (the two latest numbers, starting 0 and 1); repeat n times: replace them with (second, first + second); the first one is the answer. If you use recursion, remember it gets very slow for n around 30."],
   {"zero": "fibonacci(0) is 0, the very first number. Check your starting values.", "single": "fibonacci(1) is 1."})

ex("is_prime", 2, "Is it prime?", ["loops", "conditionals", "edge-cases"], "is_prime",
   "Write is_prime(n) that returns True if n is a prime number (greater than 1 and divisible only by 1 and itself), otherwise False.",
   "def is_prime(n):\n    pass\n",
   "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n    return True\n",
   [C([7]), C([10]), C([2], "basic"), C([1], "one"), C([0], "zero"), C([-5], "negative"), C([97], "large"), C([91], "basic", True), C([7919], "large", True), C([49], "basic", True)],
   ["A number is NOT prime if some smaller number (other than 1) divides it exactly. How can you test 'divides exactly'?",
    "Check the small cases by hand first: is 0 prime? 1? 2? A negative number? Decide those before the loop.",
    "Plan: return False for n < 2; then try each possible divisor from 2 upwards; if any divides n exactly return False; if none does return True. You only need divisors up to the square root of n."],
   {"one": "1 is not a prime number: a prime has exactly two divisors. Handle numbers below 2 before the loop.", "zero": "0 and negative numbers are not prime. Handle them before the loop.", "negative": "Negative numbers are never prime. Handle them before the loop."})

ex("word_count", 2, "Count the words", ["strings", "split", "edge-cases"], "word_count",
   "Write word_count(sentence) that returns how many words the sentence has. Words are separated by one or more spaces; there may be extra spaces at the start and end.",
   "def word_count(sentence):\n    pass\n",
   "def word_count(sentence):\n    return len(sentence.split())\n",
   [C(["hello world"]), C([""], "empty"), C(["one"], "single"), C(["  lots   of   spaces  "], "spaces"), C(["a b c d e"]), C(["   "], "spaces", True), C(["tab\tseparated words"], "spaces", True)],
   ["How would you count words in a sentence on paper? Where does each new word begin?",
    "Counting the spaces gives the wrong answer when there are extra spaces. Python has a string method that splits text into words and ignores extra whitespace.",
    "Plan: split the sentence into a list of words with .split() (with no argument), then count the list with len()."],
   {"spaces": "Extra spaces at the start, end or between words must not create extra words. Look at what .split() does with no argument.", "empty": "An empty sentence has 0 words."})

ex("remove_duplicates", 2, "Remove duplicates", ["lists", "sets", "order"], "remove_duplicates",
   "Write remove_duplicates(items) that returns a new list with repeated items removed, keeping the first occurrence of each and the original order.\nThe list you are given must not be changed.",
   "def remove_duplicates(items):\n    pass\n",
   "def remove_duplicates(items):\n    seen = set()\n    result = []\n    for item in items:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result\n",
   [C([[1, 2, 2, 3, 1]]), C([[]], "empty"), C([[5, 5, 5]], "duplicates"), C([["b", "a", "b", "c"]]), C([[3, 2, 1]], "basic"), C([[4, 4, 3, 3, 2, 2, 1]], "duplicates", True), C([[1, 2, 3, 4, 5, 1, 2, 3, 4, 5]], "duplicates", True)],
   ["Walk through the list by hand with a pencil: for each item, how do you know whether you've seen it before?",
    "A set remembers what it has seen and answers 'is x in it?' quickly. But a set doesn't keep order, so you also need a list for the result.",
    "Plan: seen = empty set; result = empty list; for each item, if it isn't in seen, add it to both seen and result; return result. Don't use list(set(items)): it loses the order."],
   {"duplicates": "When everything is repeated, only the first of each should remain. Check you add an item to the result only the first time.", "empty": "An empty list stays an empty list."})

ex("second_largest", 2, "Second largest", ["loops", "comparison", "edge-cases"], "second_largest",
   "Write second_largest(numbers) that returns the second largest DIFFERENT value, or None if there are fewer than two different values.\nExample: [4, 9, 9, 2] -> 4, because the largest is 9.",
   "def second_largest(numbers):\n    pass\n",
   "def second_largest(numbers):\n    distinct = set(numbers)\n    if len(distinct) < 2:\n        return None\n    distinct.remove(max(distinct))\n    return max(distinct)\n",
   [C([[4, 9, 2]]), C([[4, 9, 9, 2]], "duplicates"), C([[7]], "single"), C([[]], "empty"), C([[5, 5, 5]], "all-same"), C([[-1, -5, -3]], "negative"), C([[1, 2]], "basic"), C([[3, 1, 4, 1, 5, 9, 2, 6]], "basic", True), C([[2, 2, 1]], "duplicates", True)],
   ["Imagine a podium: first and second place. If two people tie for first, who is second?",
    "Duplicates of the largest value must not count as the second largest. How can you get rid of repeated values first?",
    "Plan: collect the distinct values; if fewer than 2, return None; otherwise take away the biggest one and the biggest of what's left is the answer."],
   {"duplicates": "If the biggest value appears twice, the second largest is still a smaller, different value. Work with distinct values.", "all-same": "If all values are the same there is no second largest; the exercise says what to return.", "single": "One number has no second largest.", "empty": "No numbers, no second largest."})

ex("char_frequency", 2, "Count each character", ["dictionaries", "strings", "counting"], "char_frequency",
   "Write char_frequency(text) that returns a dictionary mapping each character to how many times it appears.\nExample: 'aab' -> {'a': 2, 'b': 1}.",
   "def char_frequency(text):\n    pass\n",
   "def char_frequency(text):\n    counts = {}\n    for ch in text:\n        counts[ch] = counts.get(ch, 0) + 1\n    return counts\n",
   [C(["aab"]), C([""], "empty"), C(["hello"]), C(["a b a"], "spaces"), C(["AaA"], "uppercase"), C(["mississippi"], "basic", True), C(["zzzzzz"], "all-same", True)],
   ["Think of a tally chart: one row per character, and a mark every time you see it again.",
    "A dictionary is a tally chart. The first time you see a character it has no entry yet; how do you handle that?",
    "Plan: counts = {}; for each character: if it's already a key add 1, otherwise set it to 1 (or use counts.get(ch, 0) + 1); return counts."],
   {"empty": "An empty text gives an empty dictionary {}.", "uppercase": "'A' and 'a' are different keys unless the exercise says otherwise. Don't change the case here.", "spaces": "A space is a character too and gets its own count."})

ex("digit_sum", 2, "Sum of the digits", ["loops", "numbers", "edge-cases"], "digit_sum",
   "Write digit_sum(n) that returns the sum of the digits of the whole number n. For negative numbers ignore the minus sign.\nExample: 4821 -> 15.",
   "def digit_sum(n):\n    pass\n",
   "def digit_sum(n):\n    n = abs(n)\n    total = 0\n    while n > 0:\n        total += n % 10\n        n //= 10\n    return total\n",
   [C([4821]), C([0], "zero"), C([7], "single"), C([-123], "negative"), C([1000], "basic"), C([99999], "large", True), C([505], "basic", True)],
   ["How can you get the last digit of 4821? And how do you then 'remove' that digit to get 482?",
    "The remainder after dividing by 10 is the last digit; dividing by 10 with // (whole-number division) drops it. When do you stop?",
    "Plan: total = 0; while n is bigger than 0: add n % 10 to the total, then replace n with n // 10; return total. Take care of the minus sign first (abs)."],
   {"zero": "0 has digit sum 0. A loop that runs 'while n > 0' never runs for 0, so make sure the starting total is returned.", "negative": "The minus sign is not a digit. Use abs(n) before you start."})

# ------------------------------------------------------------------ level 3
ex("two_sum", 3, "Two numbers that add up", ["loops", "dictionaries", "indexing"], "two_sum",
   "Write two_sum(numbers, target) that returns a list [i, j] of two different positions (i < j) whose numbers add up to target, or None if there is no such pair.\nIn the tests there is never more than one right answer.",
   "def two_sum(numbers, target):\n    pass\n",
   "def two_sum(numbers, target):\n    seen = {}\n    for j, n in enumerate(numbers):\n        if target - n in seen:\n            return [seen[target - n], j]\n        seen[n] = j\n    return None\n",
   [C([[2, 7, 11, 15], 9]), C([[3, 2, 4], 6]), C([[1, 2, 3], 100], "none"), C([[], 5], "empty"), C([[3, 3], 6], "duplicates"), C([[-1, -2, -3, -4, -5], -8], "negative"), C([[5], 10], "single"), C([[0, 4, 3, 0], 0], "zero"), C([[10, 20, 30, 40, 50, 60, 70], 130], "large", True)],
   ["Pick one number. What other number would you need to reach the target? How could you find out whether it exists in the list?",
    "Looping over every pair works, but a dictionary that remembers the numbers you've already passed lets you look up 'the missing partner' directly.",
    "Plan: go through the list with positions; for each number compute its partner (target minus number); if the partner was seen before return both positions; otherwise remember this number and its position. Return None at the end."],
   {"duplicates": "The same VALUE can appear twice, at different positions. Make sure you don't use the same position twice, but do allow equal values.", "none": "If no pair exists you must return None after checking everything.", "zero": "Zero is a normal number; don't treat 0 as 'missing' (watch out for `if position:` checks).", "empty": "An empty list has no pair; return None.", "single": "One number can't pair with itself."})

ex("merge_sorted", 3, "Merge two sorted lists", ["lists", "loops", "two-pointers"], "merge_sorted",
   "Write merge_sorted(a, b) that takes two lists, each already sorted from small to large, and returns one new sorted list with all the items.\nDo it in one pass without calling sorted() on the combined list.",
   "def merge_sorted(a, b):\n    pass\n",
   "def merge_sorted(a, b):\n    result = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i])\n            i += 1\n        else:\n            result.append(b[j])\n            j += 1\n    result.extend(a[i:])\n    result.extend(b[j:])\n    return result\n",
   [C([[1, 3, 5], [2, 4, 6]]), C([[], [1, 2]], "empty"), C([[1, 2], []], "empty"), C([[], []], "empty"), C([[1, 1], [1]], "duplicates"), C([[1, 2, 3], [10, 20]], "basic"), C([[5], [1]], "single"), C([list(range(0, 40, 2)), list(range(1, 40, 2))], "large", True), C([[-3, 0], [-2, 5]], "negative", True)],
   ["Think of two queues of people, each sorted by height. Who goes next into the combined line?",
    "Keep a position in each list. Compare the two items at those positions, take the smaller, and move that position forward. What happens when one list runs out?",
    "Plan: i = j = 0; while both lists have items left, compare a[i] and b[j] and append the smaller; afterwards, whatever remains of either list is already sorted, so add it all at the end."],
   {"empty": "If one list is empty the answer is just the other one. Check your loop condition and what you add after it.", "duplicates": "Equal items are fine; make sure none get lost or doubled when the two sides are equal."})

ex("binary_search", 3, "Binary search", ["loops", "searching", "indexing"], "binary_search",
   "Write binary_search(items, target) for a list sorted from small to large with no repeated values. Return the position of target, or -1 if it isn't there.\nUse the halving idea: compare with the middle item and throw away half of the list each time.",
   "def binary_search(items, target):\n    pass\n",
   "def binary_search(items, target):\n    low, high = 0, len(items) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if items[mid] == target:\n            return mid\n        if items[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n",
   [C([[1, 3, 5, 7, 9], 7]), C([[1, 3, 5, 7, 9], 1], "edge"), C([[1, 3, 5, 7, 9], 9], "edge"), C([[1, 3, 5, 7, 9], 4], "none"), C([[], 3], "empty"), C([[5], 5], "single"), C([[5], 6], "single"), C([list(range(0, 1000, 3)), 999], "large", True), C([list(range(0, 1000, 3)), 500], "large", True)],
   ["A phone book: you open it in the middle, see if the name comes before or after, and throw half away. How do you describe 'the part still in play'?",
    "Keep two positions, low and high, for the part still in play. Look at the middle one. If it's too small, which of the two positions moves, and to where?",
    "Plan: low starts at the first position and high at the last; while low has not passed high: take the middle position (low and high added, halved, rounded down); if that item is the target return its position; if it's too small move low just past the middle, otherwise move high just before it; if the loop ends, return -1."],
   {"edge": "The first and last items are the places where off-by-one mistakes hide. Check `low <= high` (not `<`) and the +1 / -1 when moving.", "empty": "With an empty list the range is already empty. Check that high starts at -1 and the loop doesn't run.", "none": "If the target isn't there, the loop must end and return -1 instead of running forever."})

ex("gcd", 3, "Greatest common divisor", ["loops", "numbers", "algorithms"], "gcd",
   "Write gcd(a, b) that returns the greatest common divisor of two positive whole numbers: the biggest number that divides both exactly.\nExample: gcd(12, 18) = 6.",
   "def gcd(a, b):\n    pass\n",
   "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return a\n",
   [C([12, 18]), C([7, 13], "basic"), C([10, 10], "same"), C([1, 99], "one"), C([48, 18]), C([100, 25]), C([17, 5], "basic", True), C([123456, 7890], "large", True)],
   ["List the divisors of 12 and of 18 by hand. Which are shared, and which is largest?",
    "There's an old trick by Euclid: the gcd of a and b is the same as the gcd of b and the remainder of a divided by b. When can you stop?",
    "Plan: while b is not 0, replace (a, b) with (b, a % b); when b reaches 0, a is the answer."],
   {"same": "gcd(n, n) is n. Check your loop still ends with the right variable.", "one": "1 divides everything, so the answer must be 1."})

ex("balanced_brackets", 3, "Balanced brackets", ["strings", "stack", "loops"], "balanced_brackets",
   "Write balanced_brackets(text) that returns True if every (, [ and { in the text is closed by the right kind in the right order, ignoring all other characters; otherwise False.\nExamples: '([]{})' -> True, '(]' -> False, '(()' -> False.",
   "def balanced_brackets(text):\n    pass\n",
   "def balanced_brackets(text):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in text:\n        if ch in '([{':\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n",
   [C(["([]{})"]), C(["(]"]), C(["(()"], "basic"), C([""], "empty"), C(["())"], "basic"), C(["a(b[c]d)e"], "basic"), C([")("], "basic"), C(["{[()]}"], "basic", True), C(["((((((((((" + "))))))))))"], "large", True), C(["([)]"], "basic", True)],
   ["Think of nesting boxes: the last box you opened must be the first one you close.",
    "A list used as a stack (append to add, pop to remove the last) remembers the open brackets in order. What do you do with a closing bracket?",
    "Plan: for each character: opening bracket -> push; closing bracket -> the stack must not be empty and its top must be the matching opener, else return False; ignore other characters. At the end the stack must be empty."],
   {"empty": "No brackets at all is balanced (True).", "basic": "Check both kinds of failure: a closer with nothing open, and openers left over at the end."})

ex("flatten", 3, "Flatten nested lists", ["recursion", "lists", "types"], "flatten",
   "Write flatten(nested) that takes a list that may contain other lists (at any depth) and returns one flat list of all the non-list items, in order.\nExample: [1, [2, [3, 4]], 5] -> [1, 2, 3, 4, 5].",
   "def flatten(nested):\n    pass\n",
   "def flatten(nested):\n    result = []\n    for item in nested:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n",
   [C([[1, [2, [3, 4]], 5]]), C([[]], "empty"), C([[1, 2, 3]], "basic"), C([[[[]]]], "empty"), C([[[1], [2], [3]]]), C([[1, [2, [3, [4, [5]]]]]], "large", True), C([[[], 1, [[], 2]]], "empty", True)],
   ["Look at one item at a time: it's either a plain value or another list. What should you do in each case?",
    "When the item is a list, you have exactly the same problem again, on a smaller list. That is recursion: the function can call itself.",
    "Plan: result = []; for each item: if it's a list, add everything from flatten(item); otherwise append the item; return result. isinstance(item, list) tells you which case you're in."],
   {"empty": "Empty lists (even nested ones) contribute nothing. Make sure they don't add an empty list or None to the result."})

ex("run_length_encode", 3, "Run-length encoding", ["strings", "loops", "counting"], "run_length_encode",
   "Write run_length_encode(text) that compresses repeated neighbouring characters into the character followed by how many times it repeats.\nExample: 'aaabcc' -> 'a3b1c2'. An empty text gives ''.",
   "def run_length_encode(text):\n    pass\n",
   "def run_length_encode(text):\n    if not text:\n        return ''\n    parts = []\n    current, count = text[0], 1\n    for ch in text[1:]:\n        if ch == current:\n            count += 1\n        else:\n            parts.append(current + str(count))\n            current, count = ch, 1\n    parts.append(current + str(count))\n    return ''.join(parts)\n",
   [C(["aaabcc"]), C([""], "empty"), C(["a"], "single"), C(["abc"], "basic"), C(["zzzzzzzzzz"], "large"), C(["aabbaa"], "basic"), C(["a" * 25 + "b"], "large", True), C(["xxyzzz"], "basic", True)],
   ["Read 'aaabcc' aloud: three a's, one b, two c's. What do you need to remember while you read?",
    "Remember the current character and how many times you've seen it in a row. When the next character differs, what do you do with what you remembered?",
    "Plan: handle empty text; start with the first character and count 1; for each later character: same -> count + 1; different -> write the character and count to the result and start over; after the loop, don't forget to write the last group."],
   {"empty": "No characters, no groups: return ''.", "single": "One character is one group: the loop body never runs, so the last group must still be written after the loop."})

ex("rotate_list", 3, "Rotate a list", ["lists", "indexing", "modulo"], "rotate_list",
   "Write rotate_list(items, k) that returns a new list with the items moved k places to the right; the items that fall off the end come back at the front. k can be larger than the list.\nExample: ([1, 2, 3, 4, 5], 2) -> [4, 5, 1, 2, 3]. The original list must not change.",
   "def rotate_list(items, k):\n    pass\n",
   "def rotate_list(items, k):\n    if not items:\n        return []\n    k %= len(items)\n    return items[len(items) - k:] + items[:len(items) - k]\n",
   [C([[1, 2, 3, 4, 5], 2]), C([[], 3], "empty"), C([[1, 2, 3], 0], "zero"), C([[1, 2, 3], 3], "edge"), C([[1, 2, 3], 7], "large"), C([[1], 5], "single"), C([[1, 2, 3, 4], 1], "basic"), C([list(range(10)), 13], "large", True)],
   ["Try [1, 2, 3, 4, 5] with k = 1 by hand, then k = 2. What happens to the last items?",
    "Rotating by the length of the list brings you back to the start, so rotating by 7 on a list of 3 is the same as rotating by 1. Which operator gives you the remainder?",
    "Plan: if the list is empty return []; reduce k with k % len(items); the answer is the last k items followed by the rest. Slices like items[-k:] and items[:-k] help, but beware of k = 0."],
   {"empty": "Taking a remainder by len(items) fails for an empty list (division by zero). Handle the empty list first.", "zero": "k = 0 means no change. Watch out: items[-0:] is the WHOLE list, not an empty one.", "edge": "Rotating by exactly the length of the list gives back the same list.", "large": "k bigger than the list: reduce it first with %."})

ex("anagrams", 3, "Are they anagrams?", ["strings", "dictionaries", "sorting"], "anagrams",
   "Write anagrams(a, b) that returns True if the two texts use exactly the same letters the same number of times, ignoring capital letters and spaces.\nExample: 'Listen' and 'Silent' -> True.",
   "def anagrams(a, b):\n    pass\n",
   "def anagrams(a, b):\n    def clean(s):\n        return sorted(s.replace(' ', '').lower())\n    return clean(a) == clean(b)\n",
   [C(["listen", "silent"]), C(["hello", "world"]), C(["Listen", "Silent"], "uppercase"), C(["a gentleman", "elegant man"], "spaces"), C(["", ""], "empty"), C(["abc", "ab"], "basic"), C(["aab", "abb"], "duplicates"), C(["Dormitory", "dirty room"], "uppercase", True), C(["night", "thing"], "basic", True)],
   ["What must be true of two words for them to be anagrams? Think about the letters and how many of each.",
    "Two texts have the same letters exactly when, after sorting their letters, the results are equal. Which small clean-up must happen before you sort?",
    "Plan: for each text remove spaces, make it lower case, sort its letters; return whether the two sorted results are equal. Mind 'aab' vs 'abb': a set of letters isn't enough, counts matter."],
   {"uppercase": "'L' and 'l' differ for Python; convert the case first.", "spaces": "Spaces are not letters; remove them before comparing.", "duplicates": "Comparing sets of letters ignores how many times each appears. Compare sorted letters or counts instead.", "empty": "Two empty texts have the same (no) letters: True."})

ex("transpose", 3, "Transpose a matrix", ["lists", "nested-loops", "indexing"], "transpose",
   "Write transpose(matrix) that takes a list of equal-length rows and returns the matrix with rows and columns swapped.\nExample: [[1, 2, 3], [4, 5, 6]] -> [[1, 4], [2, 5], [3, 6]]. An empty matrix gives [].",
   "def transpose(matrix):\n    pass\n",
   "def transpose(matrix):\n    if not matrix:\n        return []\n    return [[row[c] for row in matrix] for c in range(len(matrix[0]))]\n",
   [C([[[1, 2, 3], [4, 5, 6]]]), C([[]], "empty"), C([[[1]]], "single"), C([[[1, 2], [3, 4]]], "basic"), C([[[1, 2, 3]]], "basic"), C([[[1], [2], [3]]], "basic"), C([[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]], "large", True)],
   ["Draw the matrix as a grid. The first row of the answer is the first column of the original: which items form it?",
    "The answer has as many rows as the original has columns. For each column number, collect that position from every original row.",
    "Plan: return [] for an empty matrix; for each column index c from 0 to (number of columns - 1) build a new row from row[c] for every row; collect those rows in a list."],
   {"empty": "An empty matrix has no first row to measure the columns from. Handle it first.", "single": "A 1x1 matrix transposes to itself."})

ex("collatz_steps", 3, "Collatz steps", ["loops", "conditionals", "numbers"], "collatz_steps",
   "Start with a positive whole number n. If it is even, halve it; if it is odd, multiply by 3 and add 1. Repeat until you reach 1.\nWrite collatz_steps(n) that returns how many steps this takes. collatz_steps(1) is 0; collatz_steps(6) is 8 (6, 3, 10, 5, 16, 8, 4, 2, 1).",
   "def collatz_steps(n):\n    pass\n",
   "def collatz_steps(n):\n    steps = 0\n    while n != 1:\n        if n % 2 == 0:\n            n //= 2\n        else:\n            n = 3 * n + 1\n        steps += 1\n    return steps\n",
   [C([6]), C([1], "one"), C([2]), C([7]), C([27], "large"), C([3]), C([97], "large", True), C([16], "basic", True)],
   ["Do 6 by hand and count each arrow. Which two rules do you apply, and when do you stop?",
    "You don't know in advance how many steps there will be, so a while loop fits. What is the condition to keep going?",
    "Plan: steps = 0; while n is not 1: if n is even replace it by n // 2, else by 3 * n + 1; add 1 to steps each time; return steps. Use // so n stays a whole number."],
   {"one": "Starting at 1 you're already done: 0 steps. Check your loop condition.", "large": "Large numbers take many steps; if your code seems stuck, check n really changes in every branch."})

ex("caesar", 3, "Caesar cipher", ["strings", "loops", "modulo"], "caesar",
   "Write caesar(text, shift) that moves every letter shift places along the alphabet (wrapping around from z to a), keeps capital letters capital, and leaves everything else unchanged. shift may be negative.\nExample: ('abc', 1) -> 'bcd'; ('xyz', 3) -> 'abc'.",
   "def caesar(text, shift):\n    pass\n",
   "def caesar(text, shift):\n    result = []\n    for ch in text:\n        if 'a' <= ch <= 'z':\n            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))\n        elif 'A' <= ch <= 'Z':\n            result.append(chr((ord(ch) - ord('A') + shift) % 26 + ord('A')))\n        else:\n            result.append(ch)\n    return ''.join(result)\n",
   [C(["abc", 1]), C(["xyz", 3], "edge"), C(["Hello, World!", 5]), C(["", 4], "empty"), C(["abc", 0], "zero"), C(["bcd", -1], "negative"), C(["abc", 27], "large"), C(["Zebra", 1], "uppercase", True), C(["a-b c", 2], "basic", True)],
   ["Write the alphabet with numbers 0 to 25 underneath. What happens to a letter when you add the shift to its number? What if it goes past 25?",
    "ord(letter) gives a number, chr(number) gives the letter back. The % 26 operator wraps numbers around. Remember that 'a' is not at 0: subtract where the alphabet starts, then add it back.",
    "Plan: for each character: if it's a lower-case letter, convert position = ord(ch) - ord('a'), add shift, % 26, convert back with chr; same with 'A' for capitals; anything else stays. Join the pieces."],
   {"edge": "Letters near the end (x, y, z) must wrap round to the start of the alphabet. The % 26 operator does that.", "negative": "A negative shift goes backwards; % 26 in Python handles it correctly, but only if you apply it after adding the shift.", "uppercase": "Capital letters start at 'A', not 'a'; and must stay capitals.", "large": "A shift of 27 is the same as 1: use % 26.", "empty": "An empty text stays empty."})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for e in EXERCISES:
        ns = {}
        exec(e["solution"], ns)
        fn = ns[e["function"]]
        cases = []
        for c in e["cases"]:
            args = copy.deepcopy(c["args"])
            expected = fn(*args)
            cases.append(dict(args=c["args"], expected=expected, tag=c["tag"], **({"hidden": True} if c["hidden"] else {})))
        if e["id"] == "two_sum":
            for c in cases:  # the prompt promises a unique answer
                nums, target = c["args"]
                pairs = [(i, j) for i in range(len(nums)) for j in range(i + 1, len(nums)) if nums[i] + nums[j] == target]
                assert len(pairs) <= 1, (nums, target, pairs)
        e = dict(e, cases=cases)
        (OUT / f"{e['id']}.json").write_text(json.dumps(e, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(EXERCISES)} exercises to {OUT}")


if __name__ == "__main__":
    main()
