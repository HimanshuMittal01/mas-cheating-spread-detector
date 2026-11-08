import sys
input = sys.stdin.readline

############ ---- Input Functions ---- ############
def inp(): 
    # one integer
    return int(input())
def input_list():
    # list of integers
    return list(map(int,input().split()))
def input_string():
    # list of characters
    s = input()
    return list(s[:len(s) - 1])
def input_int_gen():
    # integer generator 
    return map(int,input().split())

# Codeforce Educational 114
from heapq import heapify, heappop, heappush, heapreplace
# tests = inp()
tests = 1
for _ in range(tests):
    n = inp()
    avail = []
    items_count = []
    banned = set()
    for _ in range(n):
        c = input_list()
        m = c[0]
        del c[0]
        avail.append(c)
        items_count.append(m)
    m = inp()
    for _ in range(m):
        banned.add(tuple(input_list()))
    def strength(idyes):
        return sum(avail[x][idyes[x] - 1] for x in range(n))
    first = tuple(items_count)
    nexts = [(-strength(first), first)]
    while nexts:
        strn, idyes = heappop(nexts)
        strn = - strn
        if idyes not in banned:
            print(" ".join(str(y) for y in idyes))
            break
        else:
            idyes = list(idyes)
            for i in range(n):
                if idyes[i] != 0:
                    idyes[i] -= 1
                    kk = tuple(idyes)
                    heappush(nexts, (-strn + avail[i][idyes[i]] - avail[i][idyes[i] - 1], kk))
                    idyes[i] += 1
        # print(nexts)
                
        

