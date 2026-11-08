import sys
input = sys.stdin.readline
for _ in range(int(input())):
  s, n, k = map(int, input().split())
  if s < k:
    print("NO")
    continue
  if s == k:
    print("YES")
    continue

  # s > k, s >= k + 1

  # n >= 2

  if n >= k:
    if s - n >= n // k * k:
      print("NO")
      continue
  print("YES")
