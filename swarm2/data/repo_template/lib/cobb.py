def solve(n, k, a):
  x = n * (n - 1) - k * (a[-1] | a[-2])
  r = list(reversed(range(n)))
  for i in r:
    for j in r:
      if j >= i: continue
      if i * j < x: return x
      y = (i + 1) * (j + 1) - k * (a[i] | a[j])
      x = max(x, y)

  return x

t = int(input())
for i in range(t):
  n, k = map(int, input().split())
  a = list(map(int, input().split()))
  print(solve(n, k, a))
