
def solve(a,l):
    occ=[0]*len(a)
    ans=0
    n=len(a)
    if n==1:
        if a[0]==0:
            return 0
        if l[i]==1:
            return 0
        else:
            return 1
    for i in range(len(a)):
        if a[i]==1:
            if l[i]==0:
                ans+=1
                occ[i]=1
            else:
                if i!=0 and i!=n-1:
                    if l[i+1]==1 and occ[i+1]==0:
                        ans+=1
                        occ[i+1]=1
                    elif l[i-1]==1 and occ[i-1]==0:
                        ans+=1
                        occ[i-1]=1 
                elif i==0:
                    if l[i+1]==1:
                        ans+=1
                        occ[i+1]=1
                elif i==n-1:
                    if l[i-1]==1 and occ[i-1]==0:
                        ans+=1
                        occ[i-1]=1
    return ans
for _ in range(int(input())):
    n=int(input())
    l=list(map(int,input()))
    a=list(map(int,input()))
    print(solve(a,l))