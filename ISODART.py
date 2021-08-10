dataType = int(input('\nWhat type of data? (Answer 1 or 2)\n'
                     '(1) ISO Data\n'
                     '(2) Weather Data (temperature, dew point, relative humidity,\n'
                     '                  precipitation, snow depth,\n'
                     '                  wind direction, wind speed, wind peak gust,\n'
                     '                  air pressure, sunshine and weather condition)\n'))

if dataType == 1:
    iso = int(input('\nWhich ISO you want data from? (Answer 1, 2, or 3)\n'
                    '(1) California Independent system Operator (CAISO)\n'
                    '(2) Midcontinent Independent System Operator (MISO)\n'
                    '(3) New York Independent System Operator (NYISO)\n'))

    if iso == 1:
        exec(open("mainCAISO.py").read())
    elif iso == 2:
        exec(open("mainMISO.py").read())
    elif iso == 3:
        exec(open("mainNYISO.py").read())
    else:
        print("Not a valid value!")

elif dataType == 2:
    print("Loading...")
    exec(open("mainWeather.py").read())

else:
    print("Not a valid value!")
