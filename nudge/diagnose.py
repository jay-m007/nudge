"""Work out *why* a submission failed, from three kinds of evidence:

1. the Python error (syntax error, exception type and message, timeout),
2. the pattern in the wrong answers (None everywhere, off by one, wrong order ...),
3. the shape of the code itself, read with Python's ``ast`` module (a ``return``
   directly inside a loop, an accumulator reset on every pass ...).

Everything is a readable rule, so a teacher can see exactly why a hint was given.
Each finding carries texts for three hint levels; level 4 (a worked example of the
idea) comes from concepts.py.
"""
from __future__ import annotations

import ast
import builtins
import difflib
import re
from collections import Counter
from dataclasses import dataclass

from .runner import CaseResult, RunResult

EDGE_EXAMPLE = {"negative": "edge_negative", "spaces": "case_whitespace", "uppercase": "case_whitespace", "duplicates": "edge_duplicates", "zero": "zero_division", "all-same": "edge_duplicates"}
EDGE_TAGS = {"empty", "single", "zero", "negative", "duplicates", "one", "edge", "large", "all-same", "none", "short", "tie", "spaces"}


@dataclass
class Finding:
    code: str  # also the key into concepts.EXAMPLES
    concept: str  # the skill to practise; used for progress tracking
    priority: int  # lower is shown first
    line: int | None
    look: str  # hint level 1: where to look
    think: str  # hint level 2: what to think about
    point: str  # hint level 3: the specific spot
    example: str | None = None  # key into concepts.EXAMPLES
    origin: str = ""  # where the evidence came from: syntax | error | lint | answer


def _case_text(exercise: dict, case: CaseResult) -> str:
    args = ", ".join(repr(a) for a in case.args)
    return f"{exercise['function']}({args})"


# ----------------------------------------------------------------------------- syntax

def _unclosed_bracket(source: str) -> int | None:
    """Line of a bracket that is opened and never closed (or None). Older Pythons only say 'invalid syntax'."""
    import io
    import tokenize

    stack: list[tuple[str, int]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.OP:
                if tok.string in "([{":
                    stack.append((tok.string, tok.start[0]))
                elif tok.string in ")]}" and stack:
                    stack.pop()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return stack[-1][1] if stack else None


def syntax_findings(info: dict, source: str = "") -> list[Finding]:
    msg = info.get("msg", "") or ""
    line = info.get("line")
    text = info.get("text", "") or ""
    where = f"line {line}" if line else "somewhere in the file"
    look = f"Python can't read your file: it stopped at {where}. (The real problem is sometimes on the line just above.)"
    low = msg.lower()
    if re.search(r"\belse\s+if\b", text):
        return [Finding("elif", "syntax", 0, line, look, "Python has no 'else if'. It is spelled as one word.", f"Line {line}: write `elif ...:` instead of `else if ...:`.", "elif")]
    if "&&" in text or "||" in text or re.search(r"(^|[\s(])!(?!=)", text):
        return [Finding("boolean_words", "syntax", 0, line, look, "Python uses the words and, or, not instead of &&, || and !.", f"Line {line}: replace the symbols with and / or / not.", "boolean_words")]
    if re.search(r"\w(\+\+|--)", text):
        return [Finding("increment", "syntax", 0, line, look, "Python has no ++ or --. Add or subtract with += 1 or -= 1.", f"Line {line}: use `x += 1` (or `x -= 1`).", "increment")]
    opened = _unclosed_bracket(source) if source and low in ("invalid syntax", "unexpected eof while parsing") else None
    if opened:
        return [Finding("brackets", "syntax", 0, opened, look, "Look for a bracket, parenthesis or quote that is opened but not closed (or closed twice).", f"The bracket opened on line {opened} is never closed. Count the opening and closing brackets from there.", "brackets")]
    if "expected ':'" in low or (low == "invalid syntax" and re.match(r"\s*(if|elif|else|for|while|def|class|try|except|finally|with)\b[^:]*$", text)):
        return [Finding("syntax_colon", "syntax", 0, line, look, "A line that opens a block (if, for, while, def ...) must end with a colon.", f"Check the end of line {line}: is there a ':' after the condition?", "syntax_colon")]
    if re.match(r"\s*(if|elif|while)\b.*[^=!<>]=[^=]", text) and ("invalid syntax" in low or "maybe you meant '=='" in low or "cannot assign" in low):
        return [Finding("assign_vs_compare", "syntax", 0, line, look, "Inside an if or while you compare values. One '=' stores a value, two '==' compare.", f"On line {line}, the condition uses '=' where it needs '=='.", "assign_vs_compare")]
    if "unterminated string" in low or "was never closed" in low or "unmatched" in low or "closing parenthesis" in low or "perhaps you forgot a comma" in low or "unexpected eof" in low or "eol while scanning" in low or "end of file" in low:
        return [Finding("brackets", "syntax", 0, line, look, "Look for a bracket, parenthesis or quote that is opened but not closed (or closed twice).", f"Count the opening and closing brackets and quotes on line {line} and the lines around it.", "brackets")]
    if "indent" in low:
        return [Finding("indentation", "syntax", 0, line, look, "Python uses indentation to show what belongs inside a function, loop or if. Lines in the same block must line up.", f"Look at the spaces at the start of line {line} and compare them with the line above.", "indentation")]
    return [Finding("syntax_other", "syntax", 0, line, look, f"Python's message: \"{msg}\". Read it slowly; it names what it didn't expect.", f"Re-read line {line} word by word and compare it with a line of the same kind that works.", None)]


# ----------------------------------------------------------------------------- run-time errors

def _defined_names(tree: ast.AST) -> set[str]:
    names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
    return names


def _self_recursive(tree: ast.AST) -> bool:
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name for n in ast.walk(fn)):
                return True
    return False


def error_findings(err: dict, tree: ast.AST | None, source: str, where_case: str) -> list[Finding]:
    typ, msg, line = err.get("type", ""), err.get("msg", ""), err.get("line")
    at = f"line {line}" if line else "your code"
    article = "an" if typ[:1] in "AEIOU" else "a"
    if where_case == "loading your file":
        look = f"Your file raised {article} {typ} on {at} as soon as it was run."
    else:
        look = f"Your code raised {article} {typ} on {at}, when called as {where_case}."
    if typ == "NameError":
        m = re.search(r"name '(\w+)'", msg)
        name = m.group(1) if m else "?"
        near = difflib.get_close_matches(name, _defined_names(tree) if tree else [], n=1, cutoff=0.7)
        point = f"'{name}' isn't defined at {at}." + (f" You do have a name '{near[0]}': is that the one you meant?" if near else " Is it spelled differently where you created it, or never created?")
        return [Finding("name_error", "names", 2, line, look, "Python met a name it doesn't know. Names must be created before use and spelled identically.", point, "name_error")]
    if typ == "UnboundLocalError":
        return [Finding("name_error", "names", 2, line, look, "You use a variable inside the function before giving it a value there.", f"Find the variable named in the message ({msg[:80]}) and make sure it is assigned before {at}.", "name_error")]
    if typ == "ZeroDivisionError":
        return [Finding("zero_division", "edge-cases", 2, line, look, "Something was divided by zero. Which input makes the divisor zero?", f"At {at}: decide what the function should return when the divisor is 0, and check for that first.", "zero_division")]
    if typ == "IndexError":
        return [Finding("index_error", "indexing", 2, line, look, "You asked for a position that doesn't exist. Valid positions run from 0 to len - 1, and an empty list has none.", f"At {at}: what is the largest index your loop or expression can reach, and is it always smaller than len?", "index_error")]
    if typ == "KeyError":
        return [Finding("key_error", "dictionaries", 2, line, look, "You looked up a dictionary key that isn't there.", f"At {at}: check with `in` or use .get(key, default) before reading the key.", "key_error")]
    if typ == "AttributeError" and "NoneType" in msg:
        return [Finding("none_attribute", "return-values", 2, line, look, "Something is None where you expected a value. None usually means a function forgot to return.", f"At {at}: trace where that value came from. Did an earlier step end without 'return', or use a method like .sort()/.append() that returns None?", "none_attribute")]
    if typ == "TypeError":
        if "does not support item assignment" in msg and "str" in msg:
            return [Finding("string_immutable", "strings", 2, line, look, "Strings can't be changed in place.", f"At {at}: build a new string instead of assigning to a position.", "string_immutable")]
        if "can only concatenate str" in msg or "unsupported operand" in msg or "must be str" in msg or "must be real number" in msg or "can't multiply sequence" in msg:
            return [Finding("type_error", "types", 2, line, look, "You combined two things of different types, for example text and a number.", f"At {at}: check the type of each side of the operator. {msg[:100]}", "type_error")]
        if "NoneType" in msg:
            return [Finding("none_attribute", "return-values", 2, line, look, "Something is None where you expected a value, usually because of a missing return.", f"At {at}: find which value is None, then find where it should have been returned.", "none_attribute")]
        if "positional argument" in msg:
            return [Finding("type_error", "functions", 2, line, look, "A function was called with the wrong number of inputs.", f"At {at}: compare the number of values you pass with the number the function's def line lists.", None)]
        return [Finding("type_error", "types", 2, line, look, "An operation got a value of a type it can't work with.", f"At {at}: {msg[:120]}", "type_error")]
    if typ == "RecursionError":
        return [Finding("recursion_base", "recursion", 2, line, look, "The function kept calling itself and never stopped. It needs a base case, and each call must get closer to it.", f"Look at the recursive call at {at}: what makes the problem smaller, and what is the case where it stops without calling itself?", "recursion_base")]
    if typ == "Timeout" and tree is not None and _self_recursive(tree):
        return [Finding("slow_recursion", "recursion", 3, line, f"Your code ran too long on {where_case}. It may be correct but far too slow.", "When a function calls itself twice, the work doubles at every level. Even a small input can mean millions of calls.", "Either remember answers you've already worked out, or rewrite it as a loop that keeps only the values it still needs.", "slow_recursion")]
    if typ == "Timeout":
        return [Finding("infinite_loop", "loops", 3, line, f"Your code ran too long on {where_case}. It probably never finishes.", "Find the loop that runs forever. A while loop needs something inside it that eventually makes its condition false.", f"Check the while loop{' near line ' + str(line) if line else ''}: which variable in the condition changes inside it, and does it move towards stopping?", "infinite_loop")]
    if typ in ("EOFError",):
        return [Finding("input_call", "functions", 2, line, look, "Your function tries to read from the keyboard with input().", f"Remove the input() at {at}. The data arrives through the function's parameters.", "input_call")]
    if typ == "ValueError":
        return [Finding("type_error", "types", 2, line, look, "A function got a value of the right type but an unusable content, for example int('abc').", f"At {at}: {msg[:120]}", "type_error")]
    return [Finding("runtime_other", "debugging", 2, line, look, f"Python's message: \"{typ}: {msg[:100]}\". Read it for the clue.", f"Start at {at} and check each value used on that line.", None)]


# ----------------------------------------------------------------------------- code-shape lints

BUILTIN_NAMES = {"list", "str", "int", "dict", "set", "sum", "max", "min", "len", "sorted", "abs", "range", "map", "filter", "all", "any", "tuple", "float", "bool", "reversed", "enumerate", "zip", "round", "id", "type"}


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _body_walk(nodes):
    for n in nodes:
        yield from ast.walk(n)


def _loops(fn: ast.FunctionDef):
    return [n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.While))]


def lint_findings(tree: ast.AST, exercise: dict) -> list[Finding]:
    fn = _find_function(tree, exercise["function"])
    if fn is None:
        return []
    out: list[Finding] = []

    # return placed so the loop only ever runs once
    for loop in _loops(fn):
        for stmt in loop.body:
            if isinstance(stmt, ast.Return):
                out.append(Finding("return_in_loop", "loops", 4, stmt.lineno, "The answer is right only when the first item decides everything. Your loop may end too early.", "A return inside a loop ends the whole function the first time it runs.", f"Line {stmt.lineno}: this return is directly inside the loop body, so the loop runs at most once. Should it only return in certain cases, or after the loop?", "return_in_loop"))
                break
            if isinstance(stmt, ast.If) and stmt.orelse and _ends_with_return(stmt.body) and _ends_with_return(stmt.orelse):
                out.append(Finding("return_in_loop", "loops", 4, stmt.lineno, "The answer is right only when the first item decides everything. Your loop may end too early.", "If both branches of an if/else inside a loop return, the loop never gets past the first item.", f"Line {stmt.lineno}: both the if and the else return. What should happen for items that don't settle the answer yet?", "return_in_loop"))
                break

    # accumulator set up inside the loop it should live outside of
    for loop in _loops(fn):
        for i, stmt in enumerate(loop.body):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, (ast.Constant, ast.List, ast.Dict, ast.Set)):
                name = stmt.targets[0].id
                later = _body_walk(loop.body[i + 1 :])
                grows = any(isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == name for n in later) or any(
                    isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == name and n.func.attr in ("append", "add", "extend") for n in _body_walk(loop.body[i + 1 :])
                )
                returned_after = any(isinstance(n, ast.Return) and n.value is not None and any(isinstance(x, ast.Name) and x.id == name for x in ast.walk(n.value)) for n in ast.walk(fn))
                if grows and returned_after:
                    out.append(Finding("accumulator_reset", "loops", 4, stmt.lineno, "Your answer only reflects the last item, as if the earlier ones were forgotten.", "A running total or list must be created once, before the loop. Created inside, it starts over each time.", f"Line {stmt.lineno}: '{name}' is reset on every pass of the loop. Move that line above the loop.", "accumulator_reset"))

    # off-by-one in range(...)
    for n in ast.walk(fn):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name) and n.iter.func.id == "range":
            a = n.iter.args
            text = ast.unparse(n.iter)
            suspicious = False
            if len(a) == 1 and isinstance(a[0], ast.BinOp) and "len(" in ast.unparse(a[0]):
                suspicious = True  # range(len(x) - 1) / range(len(x) + 1)
            if len(a) >= 2 and isinstance(a[0], ast.Constant) and a[0].value == 1 and "len(" in ast.unparse(a[1]):
                suspicious = True  # range(1, len(x))
            if len(a) >= 2 and isinstance(a[1], ast.BinOp) and "len(" in ast.unparse(a[1]):
                suspicious = True
            if suspicious and isinstance(n.target, ast.Name) and _uses_neighbour(n, n.target.id):
                suspicious = False  # comparing x[i] with x[i-1] or x[i+1] legitimately starts at 1 or stops at len - 1
            if suspicious:
                out.append(Finding("off_by_one", "indexing", 5, n.lineno, "Your answer is close, but one item too many or too few seems to be involved.", "Check where your loop starts and where it stops. range(a, b) includes a but not b.", f"Line {n.lineno}: `for ... in {text}` - list the exact values the loop variable takes for a list of 3 items, and compare with the ones you need.", "off_by_one"))

    # changing a list while looping over it
    for n in ast.walk(fn):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Name):
            name = n.iter.id
            for m in _body_walk(n.body):
                if isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and isinstance(m.func.value, ast.Name) and m.func.value.id == name and m.func.attr in ("remove", "pop", "insert", "append", "extend", "clear"):
                    out.append(Finding("mutate_while_iterating", "lists", 4, m.lineno, "Some items get skipped or the loop misbehaves.", "Changing a list while looping over it shifts the items under the loop's feet.", f"Line {m.lineno}: you call .{m.func.attr}() on '{name}' while looping over it. Build a new list instead.", "mutate_while_iterating"))
                    break
                if isinstance(m, ast.Delete) and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == name for t in m.targets):
                    out.append(Finding("mutate_while_iterating", "lists", 4, m.lineno, "Some items get skipped or the loop misbehaves.", "Deleting from a list while looping over it shifts the items under the loop's feet.", f"Line {m.lineno}: you delete from '{name}' while looping over it. Build a new list instead.", "mutate_while_iterating"))
                    break

    # reusing a built-in's name (only a problem if the built-in is then called)
    called = {c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    for n in ast.walk(fn):
        targets = []
        if isinstance(n, ast.Assign):
            targets = [t for t in n.targets if isinstance(t, ast.Name)]
        elif isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            targets = [n.target]
        elif isinstance(n, ast.arg):
            if n.arg in BUILTIN_NAMES and n.arg in called:
                out.append(Finding("shadow_builtin", "names", 4, n.lineno, "A built-in function seems to stop working inside your function.", "Naming a variable like a built-in (list, sum, max, str ...) hides the built-in.", f"Line {n.lineno}: the parameter '{n.arg}' shares its name with a built-in. Pick another name.", "shadow_builtin"))
            continue
        for t in targets:
            if t.id in BUILTIN_NAMES and t.id in called:
                out.append(Finding("shadow_builtin", "names", 4, t.lineno, "A built-in function seems to stop working inside your function.", "Naming a variable like a built-in (list, sum, max, str ...) hides the built-in.", f"Line {t.lineno}: the variable '{t.id}' shares its name with a built-in. Pick another name.", "shadow_builtin"))

    # mutable default argument
    positional = [a.arg for a in fn.args.args]
    defaulted = dict(zip(positional[len(positional) - len(fn.args.defaults):], fn.args.defaults))
    changed_names = set()
    for m in ast.walk(fn):
        if isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and isinstance(m.func.value, ast.Name) and m.func.attr in ("append", "extend", "add", "insert", "update", "pop", "remove", "clear", "setdefault"):
            changed_names.add(m.func.value.id)
        if isinstance(m, (ast.Assign, ast.AugAssign)):
            for t in (m.targets if isinstance(m, ast.Assign) else [m.target]):
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                    changed_names.add(t.value.id)
    for name_, d in defaulted.items():
        if isinstance(d, (ast.List, ast.Dict, ast.Set)) and name_ in changed_names:
            out.append(Finding("mutable_default", "functions", 4, d.lineno, "The function gives different answers when you call it twice in a row.", "A default value like [] is created once and shared between all calls.", f"Line {d.lineno}: use None as the default and create the list inside the function.", "mutable_default"))

    # global state keeps its value between calls
    for g in ast.walk(fn):
        if isinstance(g, ast.Global):
            out.append(Finding("global_state", "functions", 4, g.lineno, "Your function's answer depends on earlier calls, not only on its input.", "A global variable keeps its value between calls, so the second call starts where the first one ended.", f"Line {g.lineno}: '{', '.join(g.names)}' is global. Create the variable inside the function so every call starts fresh.", "global_state"))
            break

    # ignores its input
    used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    params = [a.arg for a in fn.args.args]
    unused = [p for p in params if p not in used]
    if unused:
        out.append(Finding("unused_param", "functions", 5, fn.lineno, "Your function's answer doesn't depend on all of its inputs.", f"The input '{unused[0]}' is never used.", f"Line {fn.lineno}: '{unused[0]}' is never used in the function. What should it be used for?", "unused_param"))

    # input()/print instead of return
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None]
    prints = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
    if prints and not returns:
        out.append(Finding("return_vs_print", "return-values", 4, prints[0].lineno, "Your function shows something but gives nothing back.", "print displays a value on the screen; return gives it to whoever called the function.", f"Line {prints[0].lineno}: this print shows the value, but nothing is returned. Replace it with return.", "return_vs_print"))
    if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input" for n in ast.walk(fn)):
        out.append(Finding("input_call", "functions", 4, fn.lineno, "Your function waits for the keyboard.", "A function should work on its parameters, not ask the user.", "Remove input() from the function and use the parameters.", "input_call"))

    # a call whose result is thrown away, when the result is the whole point
    PURE_METHODS = {"lower", "upper", "strip", "lstrip", "rstrip", "replace", "title", "capitalize", "split", "join", "copy", "casefold"}
    PURE_FUNCS = {"sorted", "reversed", "abs", "round", "len", "sum", "max", "min", "list", "set", "int", "str", "float", "tuple"}
    for stmt in ast.walk(fn):
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            c = stmt.value
            name = None
            if isinstance(c.func, ast.Name) and (c.func.id in PURE_FUNCS or c.func.id == fn.name):
                name = c.func.id
            elif isinstance(c.func, ast.Attribute) and c.func.attr in PURE_METHODS:
                name = "." + c.func.attr + "()"
            if name:
                out.append(Finding("discarded_result", "return-values", 4, stmt.lineno, "Something your code computes seems to disappear.", "Some calls give back a new value and change nothing in place. If you don't store or return that value, it is lost.", f"Line {stmt.lineno}: you call {name} but do nothing with what it gives back. Assign it to a variable, add it to your result, or return it.", "discarded_result"))
                break

    # does not return on every path
    if returns and not _ends_with_return(fn.body) and not _ends_with_raise(fn.body):
        out.append(Finding("missing_return", "return-values", 5, fn.body[-1].lineno, "On some inputs your function gives back None.", "Every path through the function must end in a return. If no if-branch applies, Python quietly returns None.", f"The function can reach the end (after line {fn.body[-1].lineno}) without returning. What should it return then?", "none_attribute"))

    # only constants returned
    if returns and all(isinstance(r.value, ast.Constant) for r in returns) and len(exercise["cases"]) > 2 and len({repr(c["expected"]) for c in exercise["cases"]}) > 1:
        if len({r.value.value for r in returns}) == 1:
            out.append(Finding("hardcoded", "functions", 5, returns[0].lineno, "Your function gives the same answer whatever the input is.", "The answer should be worked out from the input, not written in.", f"Line {returns[0].lineno}: returns a fixed value. What would you have to compute from the input instead?", "hardcoded"))

    # recursion without a visible base case
    calls_self = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name]
    if calls_self:
        has_stop = any(isinstance(n, ast.If) and _has_return(n) for n in ast.walk(fn)) or any(
            isinstance(l, ast.For) and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn.name for c in ast.walk(l)) for l in ast.walk(fn)
        )  # a recursive call inside a loop over the input is "structural" recursion: it stops when the loop runs out
        if not has_stop:
            out.append(Finding("recursion_base", "recursion", 4, calls_self[0].lineno, "The function may never stop calling itself.", "A recursive function needs an if that returns without recursing: the base case.", f"Line {calls_self[0].lineno}: before this recursive call, there should be an if that handles the smallest input and returns.", "recursion_base"))

    # while loop whose condition never changes inside
    for n in ast.walk(fn):
        if isinstance(n, ast.While):
            names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
            changed = set()
            for m in _body_walk(n.body):
                if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store):
                    changed.add(m.id)
                if isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and isinstance(m.func.value, ast.Name):
                    changed.add(m.func.value.id)  # lst.pop(), s.add(...)
            has_exit = any(isinstance(m, (ast.Break, ast.Return)) for m in _body_walk(n.body))
            if names and not (names & changed) and not has_exit and not (isinstance(n.test, ast.Constant) and n.test.value):
                out.append(Finding("infinite_loop", "loops", 3, n.lineno, "Your program probably never finishes.", "Nothing inside the while loop changes the values its condition looks at.", f"Line {n.lineno}: the condition uses {', '.join(sorted(names))}, but none of them changes in the loop body.", "infinite_loop"))
    return out


def _uses_neighbour(loop: ast.For, var: str) -> bool:
    """Does the loop body index something with i+1 or i-1 (looking at a neighbour)?"""
    for n in _body_walk(loop.body):
        if isinstance(n, ast.Subscript):
            sl = n.slice
            if isinstance(sl, ast.BinOp) and any(isinstance(x, ast.Name) and x.id == var for x in ast.walk(sl)):
                return True
    return False


def _ends_with_return(body: list[ast.stmt]) -> bool:
    if not body:
        return False
    last = body[-1]
    if isinstance(last, ast.Return):
        return True
    if isinstance(last, ast.If):
        return bool(last.orelse) and _ends_with_return(last.body) and _ends_with_return(last.orelse)
    if isinstance(last, ast.Try):
        return _ends_with_return(last.body) and all(_ends_with_return(h.body) for h in last.handlers)
    return False


def _ends_with_raise(body: list[ast.stmt]) -> bool:
    return bool(body) and isinstance(body[-1], ast.Raise)


def _has_return(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Return) for n in ast.walk(node))



# ----------------------------------------------------------------------------- what do the failing inputs have in common?

# feature -> (the exercise tag an author may have written a tailored hint for, short description, advice)
FEATURES = {
    "capital letters": ("uppercase", "capital letters", "'A' and 'a' are different characters to Python. Does your code treat them the way the exercise wants?"),
    "spaces": ("spaces", "spaces", "A space is a character like any other. What does your code do when it meets one, or when there are extra ones?"),
    "empty input": ("empty", "empty input", "Your idea may assume there is at least one item. What does each line of your code do when there is nothing?"),
    "negative numbers": ("negative", "negative numbers", "Does anything in your code quietly assume the numbers are positive (a starting value of 0, a '> 0' test, a % or // on a negative)?"),
    "zero": ("zero", "zero", "Zero is often a special case: dividing, looping 'while n > 0', or treating 0 as 'nothing'. Check what your code does with it."),
    "repeated values": ("duplicates", "repeated values", "What does your code do when the same value shows up more than once?"),
    "a single item": ("single", "a single item", "With one item there is no 'next' or 'other' item. Does your loop or comparison still make sense?"),
    "punctuation or digits": ("", "punctuation or digits", "Characters that aren't letters must be handled too. What does your code do with them?"),
    "a very small number": ("one", "the numbers 0, 1 or 2", "Numbers at the very bottom of the range often break rules that work for bigger ones."),
}


def _flat(v):
    if isinstance(v, (list, tuple)):
        for x in v:
            yield from _flat(x)
    else:
        yield v


def input_features(args: list) -> set[str]:
    f: set[str] = set()
    for a in args:
        if isinstance(a, str):
            if a == "":
                f.add("empty input")
            if any(c.isupper() for c in a):
                f.add("capital letters")
            if " " in a:
                f.add("spaces")
            if any(not c.isalpha() and c != " " for c in a):
                f.add("punctuation or digits")
        elif isinstance(a, list):
            if not a:
                f.add("empty input")
            if len(a) == 1:
                f.add("a single item")
            atoms = [x for x in _flat(a)]
            hashable = [x for x in atoms if isinstance(x, (int, float, str, bool))]
            if len(hashable) != len(set(hashable)):
                f.add("repeated values")
            for x in atoms:
                if isinstance(x, str):
                    if x == "":
                        f.add("empty input")
                    if any(c.isupper() for c in x):
                        f.add("capital letters")
                    if " " in x:
                        f.add("spaces")
        if isinstance(a, list):
            nums = [x for x in _flat(a) if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if any(x < 0 for x in nums):
                f.add("negative numbers")
            if any(x == 0 for x in nums):
                f.add("zero")
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            if a < 0:
                f.add("negative numbers")
            if a == 0:
                f.add("zero")
            if a in (0, 1, 2):
                f.add("a very small number")
    return f


def separating_feature(result: RunResult) -> tuple[str, list[CaseResult]] | None:
    """A property of the input that every failing case has and (almost) no passing case has."""
    failing = [c for c in result.failing if not c.error]
    passing = [c for c in result.cases if c.ok]
    if not failing or not passing or len(failing) == len(result.cases):
        return None
    ff = [input_features(c.args) for c in failing]
    pf = [input_features(c.args) for c in passing]
    common = set.intersection(*ff)
    best: tuple[float, str] | None = None
    for feat in common:
        with_feat = sum(feat in p for p in pf)
        precision = len(failing) / (len(failing) + with_feat)
        if with_feat <= 2 and precision >= 0.6:
            if best is None or precision > best[0]:
                best = (precision, feat)
    return (best[1], failing) if best else None


# ----------------------------------------------------------------------------- patterns in wrong answers

def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def answer_findings(exercise: dict, result: RunResult) -> list[Finding]:
    failing = [c for c in result.failing if not c.error]
    if not failing:
        return []
    out: list[Finding] = []
    first = failing[0]
    ex_text = _case_text(exercise, first)
    look_generic = f"Your function gave a wrong answer for {ex_text}."

    if all(c.got is None for c in failing) and any(c.expected is not None for c in failing):
        printed_match = any(c.printed.strip() and c.printed.strip() == str(c.expected) for c in failing)
        if printed_match:
            out.append(Finding("return_vs_print", "return-values", 5, None, "Your function printed the right thing, but the test can't see printed text. It looks at what is returned.", "print displays a value; return hands it back to the caller.", "Replace the print(...) that shows the answer with return ...", "return_vs_print"))
        else:
            out.append(Finding("missing_return", "return-values", 5, None, f"Your function gave back None for {ex_text}.", "None means nothing was returned. Every path that produces an answer must end with return.", "Check that the line that computes the answer is followed by 'return', on every path through your function.", "none_attribute"))

    if any(c.mutated for c in failing):
        out.append(Finding("mutated_input", "lists", 5, None, f"Your function changed the input it was given (called as {ex_text}).", "The caller's list should stay the same unless the exercise says otherwise.", "Avoid .sort(), .append(), .pop(), item assignment on the parameter. Make a copy with list(...) first.", "mutated_input"))

    pairs = [(c.got, c.expected) for c in failing]
    if all(_num(g) and _num(e) for g, e in pairs):
        diffs = {g - e for g, e in pairs}
        if len(diffs) == 1 and diffs <= {1, -1} and len(failing) >= 3:
            more = "more" if next(iter(diffs)) > 0 else "less"
            out.append(Finding("off_by_one", "indexing", 5, None, f"Your answer is always exactly 1 {more} than expected (for example {ex_text}).", "A result that is consistently one off usually means a loop started or stopped one step early or late, or a count started at the wrong number.", "Look at where your loop starts and ends, and the starting value of your counter or total.", "off_by_one"))
        if any(isinstance(g, float) and isinstance(e, int) and not isinstance(e, bool) for g, e in pairs):
            out.append(Finding("integer_division", "types", 5, None, f"Your answer has a decimal point where a whole number is expected (for example {ex_text}).", "The / operator always gives a float. A whole-number result needs // (or int(...)).", "Find the division in your code and decide whether you need // instead of /.", "integer_division"))
    if all(isinstance(g, list) and isinstance(e, list) for g, e in pairs):
        if all(len(g) == len(e) and sorted(map(repr, g)) == sorted(map(repr, e)) for g, e in pairs):
            out.append(Finding("order", "lists", 5, None, f"Your list has the right items but in a different order (for example {ex_text}).", "Order matters. Check how you add items and whether the exercise says what order to keep.", "Compare, step by step, the order in which your code adds items with the order the exercise wants.", "order"))
        elif all(len(g) != len(e) for g, e in pairs):
            more = all(len(g) > len(e) for g, e in pairs)
            out.append(Finding("off_by_one", "indexing", 6, None, f"Your list has {'too many' if more else 'too few'} items (for example {ex_text}).", "Think about which items your code adds or skips by mistake.", "Walk through the first failing example by hand: which item does your code add (or skip) that it shouldn't (or should)?", "off_by_one"))
    if all(isinstance(g, (str, list)) and isinstance(e, type(g)) and len(g) < len(e) and e[: len(g)] == g for g, e in pairs):
        out.append(Finding("incomplete_output", "loops", 5, None, f"Your answer is a correct beginning, but it stops early (for example {ex_text}).", "The end of the answer is missing. Either the loop stops one step too soon (check where it starts and stops, including the very first and last items), or something held after the loop (a final count, a leftover list) is never added.", "Compare the last piece of the expected answer with yours. Which step of your code should have produced that piece, and does the loop reach it?", "incomplete_output"))
    if all(isinstance(g, str) and isinstance(e, str) and len(g) == len(e) and sorted(g) == sorted(e) for g, e in pairs):
        out.append(Finding("order", "strings", 5, None, f"Your text has the right characters, but arranged differently (for example {ex_text}).", "Check the order in which you put the pieces together.", "Compare, piece by piece, the order your code joins things with the order the exercise shows.", "order"))
    if all(isinstance(g, str) and isinstance(e, str) for g, e in pairs):
        if all(g.strip().lower() == e.strip().lower() for g, e in pairs):
            out.append(Finding("case_whitespace", "strings", 5, None, f"Your text is almost right: only capital letters or spaces differ (for example {ex_text}).", "Text must match exactly, including upper/lower case and spaces.", "Check .lower()/.upper() and .strip() where you build the result.", "case_whitespace"))
    types_expected = {type(c.expected).__name__ for c in failing}
    if len(types_expected) == 1 and all(c.got_type and c.got_type != next(iter(types_expected)) and not (c.got_type == "list" and next(iter(types_expected)) == "tuple") for c in failing):
        out.append(Finding("wrong_type", "types", 6, None, f"Your function returns a {failing[0].got_type} but a {next(iter(types_expected))} is expected ({ex_text}).", "The answer must have the right type, not just look similar.", "Check what your function returns on its last line and convert if needed.", "wrong_type"))

    got_values = {repr(c.got) for c in result.cases if not c.error}
    expected_values = {repr(c.expected) for c in result.cases}
    if len(got_values) == 1 and len(expected_values) > 1 and len(result.cases) > 2:
        only = next(iter(got_values))
        out.append(Finding("constant_answer", "functions", 6, None, f"Your function gives the same answer ({only}) for every input.", "The answer should depend on the input. If everything ends up the same, look at where the returned value comes from: a starting value that never really changes, a counter that is never increased, a base case with the wrong value, or the wrong variable returned at the end.", "Follow the returned value backwards to where it is first set. Does anything on the way change it using the input? A product that starts at 0, a counter you forgot to add to, or returning a different variable than the one you built would all give the same answer every time.", "constant_answer"))

    # which kind of input fails?
    bad_tags = {c.tag for c in failing if c.tag}
    good_tags = {c.tag for c in result.cases if c.ok and c.tag}
    edge_bad = bad_tags & EDGE_TAGS
    if edge_bad and not (bad_tags - EDGE_TAGS):
        counts = Counter(c.tag for c in failing if c.tag in EDGE_TAGS)
        tag = sorted(edge_bad, key=lambda t: (-counts[t], t))[0]
        specific = exercise.get("edge_hints", {}).get(tag)
        names = " and ".join(f"'{t}'" for t in sorted(edge_bad, key=lambda t: (-counts[t], t)))
        case_ex = _case_text(exercise, next(c for c in failing if c.tag == tag))
        out.append(Finding(f"edge_{tag}", "edge-cases", 6, None, f"Your function works on typical inputs but fails on special ones: {names} input, like {case_ex}.", specific or "Test your idea on the smallest and strangest inputs: empty, one item, zero, negative, repeated values.", f"Trace {case_ex} through your code by hand. Find the first line that behaves differently from what you assumed for this kind of input.", EDGE_EXAMPLE.get(tag, "edge_empty")))
    elif not out and (sep := separating_feature(result)):
        feat, fcases = sep
        tag, name, advice = FEATURES[feat]
        specific = exercise.get("edge_hints", {}).get(tag) if tag else None
        ex_case = _case_text(exercise, min(fcases, key=_size))
        out.append(Finding(f"fails_on_{feat.replace(' ', '_')}", "edge-cases", 6, None,
                           f"The inputs that fail have something in common: {name} (for example {ex_case}). Inputs without it mostly pass.",
                           specific or advice,
                           f"Trace {ex_case} by hand and watch what each line does with the {name}. That is where your code stops doing what you expect.",
                           EDGE_EXAMPLE.get(tag, "edge_empty")))
    elif failing and all(c.hidden for c in failing) and good_tags:
        out.append(Finding("hidden_only", "edge-cases", 7, None, "Your function passes the examples you can see but fails on others.", "Your idea may only work for the simple inputs. Think about larger or trickier ones.", "Try bigger inputs, repeated values, negative numbers and empty inputs on your own.", "edge_empty"))

    if not out:
        out.append(_contrast_finding(exercise, result, failing))
    return out


def _size(c: CaseResult) -> tuple[int, str]:
    return (len(repr(c.args)), repr(c.args))


def _first_difference(got, want) -> str | None:
    """Where two strings or lists first differ, in words."""
    if isinstance(got, str) and isinstance(want, str):
        for i, (a, b) in enumerate(zip(got, want)):
            if a != b:
                return f"the first difference is at character {i + 1}: you have {a!r}, expected {b!r}"
        if len(got) != len(want):
            return f"the first {min(len(got), len(want))} characters match, but yours is {'longer' if len(got) > len(want) else 'shorter'}"
    if isinstance(got, list) and isinstance(want, list):
        for i, (a, b) in enumerate(zip(got, want)):
            if a != b:
                return f"the first difference is at item {i + 1}: you have {a!r}, expected {b!r}"
        if len(got) != len(want):
            return f"the first {min(len(got), len(want))} items match, but your list is {'longer' if len(got) > len(want) else 'shorter'}"
    return None


def _contrast_finding(exercise: dict, result: RunResult, failing: list[CaseResult]) -> Finding:
    """No known pattern: teach the habit of debugging by contrast. Take the smallest failing
    input (easiest to trace by hand), the smallest passing one, and what differs."""
    f = exercise["function"]
    small = min(failing, key=_size)
    passing = [c for c in result.cases if c.ok]
    call = _case_text(exercise, small)
    diff = _first_difference(small.got, small.expected)
    look = f"The smallest failing input is {call}: expected {small.expected!r}, got {small.got!r}." + (f" Here {diff}." if diff else "")
    if passing:
        good = min(passing, key=_size)
        think = f"Your function works for {_case_text(exercise, good)} but not for {call}. Whatever your code does differently for these two inputs is where the bug is. What is different about them?"
    else:
        think = f"It fails every test, so the main idea probably needs rethinking. Work {call} out by hand first, writing each step down, and compare your steps with your code."
    point = f"Trace {call} through your code by hand: write down every variable after each line. The first line where a value isn't what you expected is the bug."
    return Finding("wrong_answer", "debugging", 9, None, look, think, point, None, "answer")


# ----------------------------------------------------------------------------- entry point

def _tag(findings: list[Finding], origin: str) -> list[Finding]:
    for f in findings:
        if not f.origin:
            f.origin = origin
    return findings


def diagnose(source: str, exercise: dict, result: RunResult) -> list[Finding]:
    """All findings for a failing submission, most useful first."""
    if result.status == "syntax":
        return _tag(syntax_findings(result.info, source), "syntax")
    tree: ast.AST | None
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        tree = None
    findings: list[Finding] = []
    if result.status == "load_error":
        err = result.info.get("error", {})
        findings += _tag(error_findings(err, tree, source, "loading your file"), "error")
    elif result.status == "no_function":
        defined = result.info.get("defined", [])
        name = exercise["function"]
        near = difflib.get_close_matches(name, defined, n=1, cutoff=0.6)
        point = f"Your file defines {', '.join(defined) if defined else 'no functions'}. Rename the one you mean to `{name}`." if defined else f"Add `def {name}(...)` as in the starter file."
        findings.append(Finding("no_function", "functions", 0, None, f"The tests look for a function called `{name}`, and it isn't in your file.", "The function name and its parameters must match the starter exactly." + (f" You wrote '{near[0]}'." if near else ""), point, None))
    elif result.status == "crashed":
        findings.append(Finding("crashed", "debugging", 1, None, "Your program stopped unexpectedly.", "Run your file by yourself and read the last line of the message.", "Look at the last lines of the message Python prints; they name the line.", None))
    else:
        seen_codes = set()
        for c in result.failing:
            if c.error:
                for f in _tag(error_findings(c.error, tree, source, _case_text(exercise, c)), "error"):
                    if f.code not in seen_codes:
                        seen_codes.add(f.code)
                        findings.append(f)
        findings += _tag(answer_findings(exercise, result), "answer")
    if tree is not None and result.status in ("ok", "load_error", "crashed"):
        have = {f.code for f in findings}
        findings += [f for f in _tag(lint_findings(tree, exercise), "lint") if f.code not in have]
    # keep the first finding per code, then order by priority (stable: earlier evidence first)
    seen: set[str] = set()
    unique = []
    for f in sorted(findings, key=lambda f: f.priority):
        if f.code not in seen:
            seen.add(f.code)
            unique.append(f)
    return unique
