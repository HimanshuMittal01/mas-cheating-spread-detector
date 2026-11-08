'''

* Author : Ayushman Chahar #
* About  : IT Junior       #
* Insti  : VIT, Vellore    #

'''

import os
import sys
# from collections import *
# from itertools import *
from math import gcd, log2
# from queue import *
# from heapq import *
# from bisect import *
from io import BytesIO, IOBase

BUFSIZE = 8192


class FastIO(IOBase):
    newlines = 0

    def __init__(self, file):
        self._fd = file.fileno()
        self.buffer = BytesIO()
        self.writable = "x" in file.mode or "r" not in file.mode
        self.write = self.buffer.write if self.writable else None

    def read(self):
        while True:
            b = os.read(self._fd, max(os.fstat(self._fd).st_size, BUFSIZE))
            if not b:
                break
            ptr = self.buffer.tell()
            self.buffer.seek(0, 2), self.buffer.write(b), self.buffer.seek(ptr)
        self.newlines = 0
        return self.buffer.read()

    def readline(self):
        while self.newlines == 0:
            b = os.read(self._fd, max(os.fstat(self._fd).st_size, BUFSIZE))
            self.newlines = b.count(b"\n") + (not b)
            ptr = self.buffer.tell()
            self.buffer.seek(0, 2), self.buffer.write(b), self.buffer.seek(ptr)
        self.newlines -= 1
        return self.buffer.readline()

    def flush(self):
        if self.writable:
            os.write(self._fd, self.buffer.getvalue())
            self.buffer.truncate(0), self.buffer.seek(0)


class IOWrapper(IOBase):
    def __init__(self, file):
        self.buffer = FastIO(file)
        self.flush = self.buffer.flush
        self.writable = self.buffer.writable
        self.write = lambda s: self.buffer.write(s.encode("ascii"))
        self.read = lambda: self.buffer.read().decode("ascii")
        self.readline = lambda: self.buffer.readline().decode("ascii")


sys.stdin, sys.stdout = IOWrapper(sys.stdin), IOWrapper(sys.stdout)
input = lambda: sys.stdin.readline().rstrip("\r\n")
readint = lambda: int(sys.stdin.readline().rstrip("\r\n"))
readints = lambda: map(int, sys.stdin.readline().rstrip("\r\n").split())
readstr = lambda: sys.stdin.readline().rstrip("\r\n")
readstrs = lambda: map(str, sys.stdin.readline().rstrip("\r\n").split())
readarri = lambda: [int(_) for _ in sys.stdin.readline().rstrip("\r\n").split()]
readarrs = lambda: [str(_) for _ in sys.stdin.readline().rstrip("\r\n").split()]

K = 25
MAXN = int(2e5) + 1
st = [[0 for _ in range(K + 1)] for _ in range(MAXN)]
lg = [0, 1]
for i in range(2, MAXN + 1):
    lg.append(lg[i >> 1] + 1)
arr = list()


def sparse(n):
    global st
    for j in range(n):
        st[j][0] = arr[j]
    for j in range(1, K + 1):
        for z in range(0, n + 1 - (1 << j)):
            st[z][j] = gcd(st[z][j - 1], st[z + (1 << (j - 1))][j - 1])


def query(l, r):
    f = lg[r - l + 1] - 1
    return gcd(st[l][f], st[r - (1 << f) + 1][f])


def solve():
    global arr
    n = readint()
    a = readarri()
    if (n == 1):
        print(1)
        return
    arr = [0] * (n - 1)
    for i in range(n - 1):
        arr[i] = abs(a[i + 1] - a[i])
    sparse(n - 1)
    ans = ptr = 0
    for i in range(n - 1):
        while (ptr <= i and query(ptr, i) == 1):
            ptr += 1
        ans = max(ans, abs(ptr - i) + 2)
    print(ans)


def main():
    t = 1
    t = readint()
    for _ in range(t):
        # print("Case #" + str(_ + 1) + ": ", end="")
        solve()


if __name__ == "__main__":
    main()
