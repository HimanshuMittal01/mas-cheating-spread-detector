import math
for _ in range(int(input())):
    n,m=map(int,input().split())
    a=" "
    b=0
    li=[]
    for i in range(32):
        li.append(i)
    if(n>m):
        print(0)
    else:
        a=bin(n)[2:]
        b=len(a)
        i=b-1
        j=0
        while(i>=0):
            if(a[i]=="1"):
                li.remove(j)
            j=j+1 
            i=i-1
        li.append(-1)
        x=n 
        k=m-n+1
        while(x<=m):
            y=int(math.log(k,2))
            for i in range(len(li)):
                if(li[i]>=y and li[i-1]<y ):
                    y=li[i]
                    # print(li)
                    break
            x=x+(2**y)
            k=k-(2**y)
            # print(x,k,y,li)
        print(x-n)