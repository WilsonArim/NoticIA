---
name: Systematic Debugging
description: Methodical debugging with hypotheses instead of random changes
phase: 0
always_active: true
---

# Systematic Debugging

Debugging is not guessing. It is a disciplined process of forming hypotheses and
testing them. Random changes waste time and often introduce new bugs.

## Core Principle

Every debugging session follows a protocol. You never change code without a hypothesis
about why that change will fix the problem.

## The Debug Protocol

Follow these five steps in order. Do not skip steps.

### Step 1: Reproduce
Before anything else, reproduce the bug reliably.
- Get the exact error message, stack trace, or incorrect behavior.
- Identify the minimum steps to trigger the issue.
- Note the environment: OS, Node version, browser, database state.
- If you cannot reproduce it, you cannot fix it. Gather more information first.

### Step 2: Hypothesize
Form a specific, testable hypothesis about the cause.
- BAD: "Something is wrong with the database"
- GOOD: "The query in getUserById returns null because the id parameter is a string
  but the column type is integer, causing a type mismatch in the WHERE clause"

Write your hypothesis down. This prevents you from drifting into random exploration.

### Step 3: Test
Design a minimal test for your hypothesis.
- Add a targeted log statement or breakpoint.
- Write a failing test case that captures the bug.
- Inspect the specific variable, query, or response you suspect.
- Do NOT change multiple things at once. Test one hypothesis at a time.

### Step 4: Fix
Apply the smallest possible change that addresses the confirmed root cause.
- Fix the root cause, not the symptom.
- If the fix is more than 10 lines, pause and reconsider whether you found the
  real root cause.
- Do not add workarounds unless you document why and create a follow-up task.

### Step 5: Verify
Confirm the fix works and has no side effects.
- Reproduce the original bug scenario -- it should be gone.
- Run the full test suite.
- Check related functionality for regressions.
- Remove any temporary debug logging or breakpoints.

## When NOT to Debug

Sometimes the answer is right in front of you. Before entering the debug protocol:

1. **Read the error message.** Many developers skip the actual error text. Read it
   carefully, word by word. Most error messages tell you exactly what is wrong.
2. **Read the stack trace.** Find YOUR code in the stack trace (ignore framework
   internals). The bug is almost always at the boundary between your code and the
   library code.
3. **Check the obvious.** Typos, missing imports, wrong file paths, undefined
   environment variables. A 5-second check saves a 30-minute investigation.
4. **Search the error.** Paste the exact error message into your search engine. If
   thousands of people have hit the same error, the fix is documented.

## Binary Search Technique

When you have no idea where the bug is, use binary search to narrow it down.

### For Logic Bugs
1. Find a known-good state and a known-bad state in your data flow.
2. Add a checkpoint at the midpoint.
3. If the data is correct at the midpoint, the bug is in the second half.
4. If incorrect, the bug is in the first half.
5. Repeat until you isolate the exact line or function.

### For Regressions
1. Find a commit where the feature worked (git log / git bisect).
2. Find the current broken commit.
3. Use `git bisect` to binary search through commits.
```
git bisect start
git bisect bad HEAD
git bisect good abc1234
# Test each commit git bisect suggests
git bisect good  # or git bisect bad
```

### For Configuration Issues
1. Start with a minimal working configuration.
2. Add settings back one at a time until the bug appears.
3. The last added setting is the culprit.

## Logging Strategy

### Effective Debug Logging
- Log INPUTS and OUTPUTS of the suspected function.
- Include timestamps when investigating timing issues.
- Log the ACTUAL value, not just "value exists": `console.log('userId:', userId)`
  not `console.log('has userId')`.
- Use structured logging: `{ event: 'query_failed', table: 'users', error: err.message }`.

### What to Log at Each Level
- **ERROR**: Something failed that should not have. Requires attention.
- **WARN**: Something unexpected happened but the system recovered.
- **INFO**: Significant business events (user created, payment processed).
- **DEBUG**: Detailed technical information for troubleshooting. Never in production.

### Cleanup Rule
All debug logging added during investigation MUST be removed or converted to
appropriate permanent logging before the fix is merged.

## Common Debugging Patterns

### The Null Reference
Symptom: "Cannot read property X of undefined"
Protocol: Trace the variable backward from the error to its source. Find where it
was supposed to be assigned and why it was not.

### The Race Condition
Symptom: Works sometimes, fails sometimes. Passes locally, fails in CI.
Protocol: Look for shared mutable state, missing await keywords, unguarded async
operations. Add sequencing or locking.

### The Silent Failure
Symptom: No error, but wrong behavior.
Protocol: Add assertions at key points. Check for swallowed exceptions (empty catch
blocks). Verify return values are being used.

### The Environment Bug
Symptom: Works on my machine.
Protocol: Compare environment variables, package versions, OS, database state. Use
`diff` on configuration files between environments.

## Rules

1. NEVER change code without a hypothesis about why that change will fix the issue.
2. ALWAYS reproduce the bug before attempting to fix it.
3. ALWAYS read the full error message and stack trace first.
4. TEST one hypothesis at a time. Never change multiple things simultaneously.
5. FIX the root cause, not the symptom.
6. VERIFY the fix by reproducing the original failure scenario.
7. CLEAN UP all temporary debug code before committing.
8. DOCUMENT non-obvious bugs with a comment explaining what went wrong and why.
9. WRITE a regression test for every bug you fix.
10. TIME-BOX your investigation. If stuck for 30 minutes, step back and reassess.
