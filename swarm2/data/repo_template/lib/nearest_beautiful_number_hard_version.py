def solve(num, k):
    count = 0
    tab = [-1 for _ in range(int(k))]
    idx = 0
    rem = -1
    rem_idx = -1
    for x in num:
        if int(x) not in tab:
            if count < int(k):
                tab[count] = int(x)
                count += 1
            else:
                rem = int(x)
                rem_idx = idx
                break
        idx += 1

    if rem != -1:
        check = False
        counter = 0
        sec_tab = []
        new = min(tab)
        if max(rem, max(tab)) == rem:
            for x in num:
                if int(x) not in sec_tab and not check:
                    if counter == count-1:
                        print(int(x)+1, end = "")
                        check = True

                        if int(x) == min(tab):
                            if int(x)+1 not in tab:
                                new = int(x)+1
                                # for i in range(len(tab)):
                                #     if tab[i] == int(x):
                                #         tab[i] += 1
                                #         break
                            else:
                                new = min([i for i in range(10) if i not in tab])

                    else:
                        sec_tab.append(int(x))
                        counter += 1
                        print(int(x), end = "")

                elif not check:
                    print(int(x), end="")

                else:
                    print(new, end="")

            print()

        else:
            temp = min([i for i in tab if i > rem])
            for x in num:
                if int(x) not in sec_tab and not check:
                    if counter == count:
                        print(temp, end="")
                        check = True
                    else:
                        sec_tab.append(int(x))
                        counter += 1
                        print(int(x), end="")

                elif not check:
                    print(int(x), end="")

                else:
                    print(min(tab), end="")

            print()

    else:
        print(num)

for _ in range(int(input())):
    num, k = map(str, input().split())
    solve(num, k)


