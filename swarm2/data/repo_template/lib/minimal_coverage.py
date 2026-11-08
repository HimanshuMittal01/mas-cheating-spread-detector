import io,os
import sys
input = io.BytesIO(os.read(0, os.fstat(0).st_size)).readline

sys.setrecursionlimit(10010)

def getnext(index,curr,minimum,maximum,arr,dic):

    if index==len(arr):  return minimum
    if (index,curr) in dic:  return dic[(index,curr)]
    
    if curr + arr[index] <= maximum:
        num1 = getnext(index+1,curr+arr[index],minimum,maximum,arr,dic)
    else:
        num1 = -2147483648


    num2 = getnext(index+1,curr-arr[index],min(minimum,curr-arr[index]),maximum,arr,dic)

    dic[(index,curr)] = max(num1,num2)
    return max(num1,num2)


    




def main(t):


    n = int(input())
    arr = list(map(int,input().split()))

    ans = 2147483647

    rmax = max(arr)
    for maximum in range(rmax,0,-1):
        dic = {}
        minimum = getnext(0,0,0,maximum,arr,dic)
#        print(maximum,minimum)


        ans = min(ans, maximum-minimum)


    print(ans)




















T = int(input())
t = 1
while t<=T:
    main(t)
    t += 1
