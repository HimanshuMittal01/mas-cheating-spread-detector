import sys
for _ in range(int(sys.stdin.readline())):
    n = int(sys.stdin.readline())
    s = sys.stdin.readline().strip()
    d = [0] * 27
    l = [0] * 26
    for i in range(len(s)-1, -1, -1):
        p = ord(s[i])-97
        t = max(d[p+1:])
        lp = l[p]
        if lp != 0:
            j = 1
            while lp + j < len(s) and s[lp+j] == s[i+j]: j += 1
            if lp + j < len(s) and s[lp+j] > s[i+j]: 
                t = max(t, d[p] - j)
        d[p] = t + len(s) - i
        l[p] = i
    sys.stdout.write("%d\n" % max(d))
