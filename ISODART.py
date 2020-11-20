iso = int(input('\nWhich ISO you want data from? (Answer 1 or 2)\n'
                '(1) California Independent system Operator (CAISO)\n'
                '(2) New York Independent System Operator (NYISO)\n'))

if iso == 1:
    exec(open("mainCAISO.py").read())
elif iso == 2:
    exec(open("mainNYISO.py").read())
else:
    print("Not a valid value!")

print ("Some CRAZY STUFF")