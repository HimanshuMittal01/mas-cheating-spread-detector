from bisect import bisect
from collections import defaultdict
from sys import stdin


def input():
    return next(stdin)[:-1]


def readline():
    return map(int, input().split())


primes = [2]
for q in range(3, 10**3, 2):
    if all(q % p for p in primes):
        primes.append(q)


def prime_divisors(n, primes=primes):
    ret = []
    for p in primes:
        if p * p > n:
            break
        q, r = divmod(n, p)
        if not r:
            ret.append(p)
        while not r:
            n = q
            q, r = divmod(n, p)
    if n > 1:
        ret.append(n)
    return ret


def test_prime_divisors():
    assert list(prime_divisors(6)) == [2, 3]
    assert list(prime_divisors(9)) == [3]
    assert list(prime_divisors(10)) == [2, 5]
    assert list(prime_divisors(7)) == [7]
    assert list(prime_divisors(997)) == [997]
    assert list(prime_divisors(1009)) == [1009]


class DSU:
    __slots__ = ('p',)

    def __init__(self):
        self.p = list(range(10**6))

    def _get_root(self, a):
        while self.p[a] != a:
            a = self.p[a]
        return a

    def __setitem__(self, a, b):
        assert b <= a
        r = self._get_root(b)
        while a != r:
            self.p[a], a = r, self.p[a]

    def __getitem__(self, a):
        self[a] = a
        return self.p[a]


def main():
    n, q = readline()
    a = list(readline())
    queries = (readline() for __ in range(q))

    min_divisor = list()
    dsu = DSU()
    for ai in a:
        p, *rest = prime_divisors(ai)
        min_divisor.append(p)
        for q in rest:
            dsu[q] = p

    for i in range(len(dsu.p)):
        dsu[i]
    dsu = dsu.p

    components = sorted(dsu[p] for p in min_divisor)

    available = [set() for __ in range(len(components))]
    for (ai, p) in zip(a, min_divisor):
        p = dsu[p]
        if p != dsu[2]:
            idx = bisect(components, p) - 1
            assert idx >= 0
            available[idx].update(dsu[q] for q in prime_divisors(ai + 1))

    def av(p, q):
        return p in available[bisect(components, q) - 1]

    for (s, t) in queries:
        p = dsu[min_divisor[s-1]]
        q = dsu[min_divisor[t-1]]
        if p == q:
            print(0)
        elif dsu[2] in (p, q) or av(p, q) or av(q, p):
            print(1)
        else:
            print(2)


if __name__ == '__main__':
    main()


# t.me/belkka
