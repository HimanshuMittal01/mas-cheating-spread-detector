def side(chord, i, n):
    a, b = chord
    a, b  = min(a, b), max(a, b)
    if b-a==n and (i < a or i > b):
        return 'Small'
    elif b-a==n and (i < a < b):
        return 'Large'
    elif b-a < n and a < i < b:
        return 'Small'
    elif b-a> n and (i > b or i < a):
        return 'Small'
    else:
        return 'Large'
    
def process(n, chords):
    k = len(chords)
    answer = (n-k)*(n-k-1)//2
    answer2 = 0
    for a, b in chords:
        a, b = min(a, b), max(a, b)
        for a1, b1 in chords:
            S1 = side([a, b], a1, n)
            S2 = side([a, b], b1, n)
            if abs(b1-a1)==n and abs(b-a)==n:
                answer2+=1
            elif S1 != S2:
                answer2+=1
    S = set([])
    for a, b in chords:
        S.add(a)
        S.add(b)
    answer2 = answer2//2
    answer3 = 0
    d = {}
    for i in range(1, 2*n+1):
        if i not in S:
            for c in chords:
                if c[0] not in d:
                    d[c[0]] = [0, 0]
                if side(c, i, n)=='Small':
                    d[c[0]][0]+=1
                else:
                    d[c[0]][1]+=1
    for c in d:
        answer3+=min(d[c][0], d[c][1])
    return answer+answer2+answer3

t = int(input())
for i in range(t):
    n, k  = [int(x) for x in input().split()]
    chords = []
    for j in range(k):
        a, b = [int(x) for x in input().split()]
        chords.append([a, b])
    print(process(n, chords))