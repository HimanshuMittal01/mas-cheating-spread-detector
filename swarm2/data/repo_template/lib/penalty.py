t=int(input())
for x in range(t):
    strr=list(input())
    Ga=0
    Gb=0
    A=5
    B=5
    for i in range(10):
        if i%2==0 and strr[i]=='?':
            strr[i]=1
        if i%2==1 and strr[i]=='?':
            strr[i]=0
        if i%2==0:
            Ga+=int(strr[i])
            A-=1
        if i%2==1:
            Gb+=int(strr[i])
            B-=1
        if Ga>Gb+B and Ga>=1:
            print(i+1)
            break
        if Gb>Ga+A and Gb>=1:
            print(i+1)
            break
        if i==9:
            print(10)
        
        