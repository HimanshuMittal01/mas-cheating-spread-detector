`lib/cherry.py` gives wrong answers on some inputs. The tests in `tests/` describe the expected behaviour. The fix belongs in `lib/cherry.py`.

You are given n integers a_1, a_2, …, a_n. Find the maximum value of max(a_l, a_{l + 1}, …, a_r) ⋅ min(a_l, a_{l + 1}, …, a_r) over all pairs (l, r) of integers for which 1 ≤ l < r ≤ n.

Input

The first line contains a single integer t (1 ≤ t ≤ 10 000) — the number of test cases.

The first line of each test case contains a single integer n (2 ≤ n ≤ 10^5).

The second line of each test case contains n integers a_1, a_2, …, a_n (1 ≤ a_i ≤ 10^6).

It is guaranteed that the sum of n over all test cases doesn't exceed 3 ⋅ 10^5.

Output

For each test case, print a single integer — the maximum possible value of the product from the statement.

Example

Input


4
3
2 4 3
4
3 2 3 1
2
69 69
6
719313 273225 402638 473783 804745 323328


Output


12
6
4761
381274500335

Note

Let f(l, r) = max(a_l, a_{l + 1}, …, a_r) ⋅ min(a_l, a_{l + 1}, …, a_r).

In the first test case, 

  * f(1, 2) = max(a_1, a_2) ⋅ min(a_1, a_2) = max(2, 4) ⋅ min(2, 4) = 4 ⋅ 2 = 8. 
  * f(1, 3) = max(a_1, a_2, a_3) ⋅ min(a_1, a_2, a_3) = max(2, 4, 3) ⋅ min(2, 4, 3) = 4 ⋅ 2 = 8. 
  * f(2, 3) = max(a_2, a_3) ⋅ min(a_2, a_3) = max(4, 3) ⋅ min(4, 3) = 4 ⋅ 3 = 12. 



So the maximum is f(2, 3) = 12.

In the second test case, the maximum is f(1, 2) = f(1, 3) = f(2, 3) = 6.
