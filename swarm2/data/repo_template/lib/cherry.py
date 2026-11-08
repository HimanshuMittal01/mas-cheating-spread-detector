'''Author- Nipun Jain'''
import os,sys;
import itertools
from io import BytesIO, IOBase
BUFSIZE = 8192
class FastIO(IOBase):
    newlines = 0
    def __init__(self, file):
        self._fd = file.fileno();self.buffer = BytesIO();self.writable = "x" in file.mode or "r" not in file.mode;self.write = self.buffer.write if self.writable else None
    def read(self):
        while True:
            b = os.read(self._fd, max(os.fstat(self._fd).st_size, BUFSIZE))
            if not b:break
            ptr = self.buffer.tell();self.buffer.seek(0, 2), self.buffer.write(b), self.buffer.seek(ptr)
        self.newlines = 0
        return self.buffer.read()
    def readline(self):
        while self.newlines == 0:b = os.read(self._fd, max(os.fstat(self._fd).st_size, BUFSIZE));self.newlines = b.count(b"\n") + (not b);ptr = self.buffer.tell();self.buffer.seek(0, 2), self.buffer.write(b), self.buffer.seek(ptr)
        self.newlines -= 1
        return self.buffer.readline()
    def flush(self):
        if self.writable:os.write(self._fd, self.buffer.getvalue());self.buffer.truncate(0), self.buffer.seek(0)
class IOWrapper(IOBase):
    def __init__(self, file):
        self.buffer = FastIO(file);self.flush = self.buffer.flush;self.writable = self.buffer.writable;self.write = lambda s: self.buffer.write(s.encode("ascii"));self.read = lambda: self.buffer.read().decode("ascii");self.readline = lambda: self.buffer.readline().decode("ascii")
sys.stdin, sys.stdout = IOWrapper(sys.stdin), IOWrapper(sys.stdout)
try:
    sys.stdin,sys.stdout=open('input.txt','r'),open('output.txt','w')
except:
    pass
mod=int(1e9 + 7);from collections import *;
import math
from sys import stdin, stdout
def input_array():
    return list(map(int, stdin.readline().split()))
def input_one():
    return int(stdin.readline())
def input_two():
    a, b = map(int, stdin.readline().split())
    return a, b
def input_three():
    a, b, c = map(int, stdin.readline().split())
    return a, b, c
def input_four():
    a, b, c, d = map(int, stdin.readline().split())
    return a, b, c, d
def input_five():
    a, b, c, d, e = map(int, stdin.readline().split())
    return a, b, c, d, e
def input_six():
    a, b, c, d, e, f = map(int, stdin.readline().split())
    return a, b, c, d, e, f
def input_s():
    s=input()
    return s
# sys.setrecursionlimit(500000)
###################### Start Here ######################
    
n=int(input())
for i in range(n):
    t=int(input())
    l=[int(x) for x in input().split()]
    # a=sorted(l)
    count=0
    for i in range(0,t):
        count=max(count,l[i]*l[i-1])
    print(count)
