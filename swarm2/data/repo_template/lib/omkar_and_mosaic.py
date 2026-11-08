import sys
o = {'G':'S', 'S':'G'}
n = int(sys.stdin.readline())
d = [list(sys.stdin.readline()[:n]) for _ in range(n)]
f = [1]*(n*n)
finished = 1
def none(): sys.stdout.write('NONE\n'); sys.exit()
def printd(): print('\n'.join(''.join(d[i]) for i in range(n)))
if n % 2: none()
def fill(a,b):
    c = d[a][b]
    if (a+b) % 2 == 0: 
        s = min(a,n-1-b)
        y, x = a - s, b + s
        while y < n and x >= 0:
            g1 = o[c] if (y - a) % 2 else c
            if d[y][x] == o[g1]: none()
            else:
                d[y][x] = g1
                f[y*n+x] = 0
            x-=1; y+=1;
    else:
        s = min(a,b)
        y, x = a - s, b - s
        while y < n and x < n:
            g1 = o[c] if (y - a) % 2 else c
            if d[y][x] == o[g1]: none()
            else:
                d[y][x] = g1
                f[y*n+x] = 0
            x+=1; y+=1;
        
def get(a,b): return d[a][b] if 0<=a<n and 0<=b<n else ''
def checkfill(a,b):
    global finished
    x = get(a+1,b)+get(a,b+1)+get(a-1,b)+get(a,b-1)
    g,s,z = x.count('G'), x.count('S'), x.count('.')
    if d[a][b] == '.': 
        if g>2 or s>2: none()
        elif g==2: d[a][b] = 'G'; fill(a,b); return 1
        elif s==2: d[a][b] = 'S'; fill(a,b); return 1
        finished = 0
    else:
        if z == 1:
            g += d[a][b] == 'G'; s += d[a][b] == 'S'
            x = 'G' if g == 2 or g == 0 else 'S'
            if get(a+1,b) == '.': d[a+1][b] = x; fill(a+1,b)
            elif get(a,b+1) == '.': d[a][b+1] = x; fill(a, b+1)
            elif get(a-1,b) == '.': d[a-1][b] = x; fill(a-1, b)
            else: d[a][b-1] = x; fill(a, b-1)
            return 1
    return 0

for i in range(n):
    for j in range(n):
        if d[i][j] != '.' and f[i*n+j]:
            fill(i, j)
r = 1
while r:
    r = 0
    for i in range(n):
        r |= checkfill(i, 0)
        r |= checkfill(i, n-1)
        r |= checkfill(0, i)
        r |= checkfill(n-1, i)
if finished: print('UNIQUE'); printd()
else: print('MULTIPLE')
