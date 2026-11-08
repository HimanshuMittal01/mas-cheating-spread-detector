`lib/mikasa.py` gives wrong answers on some inputs. The tests in `tests/` describe the expected behaviour. The fix belongs in `lib/mikasa.py`.

You are given two integers n and m. Find the \operatorname{MEX} of the sequence n ⊕ 0, n ⊕ 1, …, n ⊕ m. Here, ⊕ is the [bitwise XOR operator](https://en.wikipedia.org/wiki/Bitwise_operation#XOR).

\operatorname{MEX} of the sequence of non-negative integers is the smallest non-negative integer that doesn't appear in this sequence. For example, \operatorname{MEX}(0, 1, 2, 4) = 3, and \operatorname{MEX}(1, 2021) = 0. 

Input

The first line contains a single integer t (1 ≤ t ≤ 30 000) — the number of test cases.

The first and only line of each test case contains two integers n and m (0 ≤ n, m ≤ 10^9).

Output

For each test case, print a single integer — the answer to the problem.

Example

Input


5
3 5
4 6
3 2
69 696
123456 654321


Output


4
3
0
640
530866

Note

In the first test case, the sequence is 3 ⊕ 0, 3 ⊕ 1, 3 ⊕ 2, 3 ⊕ 3, 3 ⊕ 4, 3 ⊕ 5, or 3, 2, 1, 0, 7, 6. The smallest non-negative integer which isn't present in the sequence i. e. the \operatorname{MEX} of the sequence is 4.

In the second test case, the sequence is 4 ⊕ 0, 4 ⊕ 1, 4 ⊕ 2, 4 ⊕ 3, 4 ⊕ 4, 4 ⊕ 5, 4 ⊕ 6, or 4, 5, 6, 7, 0, 1, 2. The smallest non-negative integer which isn't present in the sequence i. e. the \operatorname{MEX} of the sequence is 3.

In the third test case, the sequence is 3 ⊕ 0, 3 ⊕ 1, 3 ⊕ 2, or 3, 2, 1. The smallest non-negative integer which isn't present in the sequence i. e. the \operatorname{MEX} of the sequence is 0.
