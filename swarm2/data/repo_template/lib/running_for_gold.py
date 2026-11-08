for hbdcjcsk in range(int(input())):
    n=int(input())
    a={}
    for i in range(1,n+1):
        l=list(map(int,input().split()))
        a[i]=l
    ans=-1
    for i in a:
        sum=50000*5-(a[i][0]+a[i][1]+a[i][2]+a[i][3]+a[i][4])
        if sum<n-1:
            break
        sup=True
        for j in a:
            if j!=i:
                count=0
                if a[i][0]<a[j][0]:
                    count+=1
                if a[i][1]<a[j][1]:
                    count+=1
                if a[i][2]<a[j][2]:
                    count+=1
                if a[i][3]<a[j][3]:
                    count+=1
                if a[i][4]<a[j][4]:
                    count+=1
                if count<3:
                    sup=False
                    break
        if sup:
            ans=i
            break
    print(ans)