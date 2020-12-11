from lib.framework.NYISO.query import *
from lib.framework.NYISO.merge import *
import datetime

raw_dir = os.path.join(os.getcwd(), 'raw_data', 'NYISO')
data_dir = os.path.join(os.getcwd(), 'data', 'NYISO')

if os.path.isdir(raw_dir):
    pass
else:
    os.makedirs(raw_dir)

if os.path.isdir(data_dir):
    pass
else:
    os.makedirs(data_dir)

ind = 1
while ind == 1:
    print('\nPlease enter the start date and duration of the desired data set.')
    month = int(input('Month: '))
    day = int(input('Day: '))
    year = int(input('Year (4-digit format): '))
    try:
        datetime.datetime(year=year, month=month, day=day)
        ind = 0
    except:
        print('\nWARNING: The Date Does NOT Exist. Please Try Again!!')

duration = int(input('Duration (in days): '))

data_type = int(input('What type of data? (Answer 1, 2, or 3)\n'
                      '(1) Pricing Data\n'
                      '(2) Power Grid Data\n'
                      '(3) Load Data\n'))

if data_type == 1:
    price = int(input('\nWhat type of pricing data? (Answer 1 or 2)\n'
                      '(1) Locational Based Marginal Prices (LBMP)\n'
                      '(2) Ancillary Services Prices\n'))

    market = int(input('\nWhich energy market? (Answer 1 or 2)\n'
                       '(1) Day-Ahead Market (DAM)\n'
                       '(2) Real-Time Market (RTM)\n'))

    if price == 1:
        level = int(input('\nWhat degree of detail? (Answer 1 or 2)\n'
                          '(1) Zonal\n'
                          '(2) Generator\n'))

    if price == 1 and market == 1 and level == 1:
        dataid = 'damlbmp'
        aggType = 'zone'
        filenamedataid = dataid

    elif price == 1 and market == 1 and level == 2:
        dataid = 'damlbmp'
        aggType = 'gen'
        filenamedataid = dataid

    elif price == 1 and market == 2 and level == 1:
        dataid = 'realtime'
        aggType = 'zone'
        filenamedataid = dataid

    elif price == 1 and market == 2 and level == 2:
        dataid = 'realtime'
        aggType = 'gen'
        filenamedataid = dataid

    elif price == 2 and market == 1:
        dataid = 'damasp'
        aggType = None
        filenamedataid = dataid

    elif price == 2 and market == 2:
        dataid = 'rtasp'
        aggType = None
        filenamedataid = dataid

elif data_type == 2:
    power_grid = int(input('\nWhat type of power grid data? (Answer 1 or 2)\n'
                           '(1) Outages\n'
                           '(2) Constraints\n'))

    market = int(input('\nWhich energy market? (Answer 1 or 2)\n'
                       '(1) Day-Ahead Market (DAM)\n'
                       '(2) Real-Time Market (RTM)\n'))

    if power_grid == 1 and market == 2:
        outage_type = int(input('\nWhat type of outages? (Answer 1 or 2)\n'
                                '(1) Scheduled\n'
                                '(2) Actual\n'))

    if power_grid == 1 and market == 1:
        dataid = 'outSched'
        aggType = None
        filenamedataid = dataid

    elif power_grid == 1 and market == 2 and outage_type == 1:
        dataid = 'schedlineoutages'
        aggType = None
        filenamedataid = 'SCLineOutages'

    elif power_grid == 1 and market == 2 and outage_type == 2:
        dataid = 'realtimelineoutages'
        aggType = None
        filenamedataid = 'RTLineOutages'

    elif power_grid == 2 and market == 1:
        dataid = 'DAMLimitingConstraints'
        aggType = None
        filenamedataid = dataid

    elif power_grid == 2 and market == 2:
        dataid = 'LimitingConstraints'
        aggType = None
        filenamedataid = dataid

elif data_type == 3:
    load = int(input('\nWhat type of load data? (Answer 1 or 2)\n'
                     '(1) Load Forecast/Commitment\n'
                     '(2) Actual Load\n'))

    if load == 1:
        forecast = int(input('\nWhat type of load forecast/commitment data? (Answer 1, 2, or 3)\n'
                             '(1) ISO Load Forecast\n'
                             '(2) Zonal Bid Load\n'
                             '(3) Weather Forecast\n'))

        if forecast == 1:
            dataid = 'isolf'
            aggType = None
            filenamedataid = dataid

        elif forecast == 2:
            dataid = 'zonalBidLoad'
            aggType = None
            filenamedataid = dataid

        elif forecast == 3:
            dataid = 'lfweather'
            aggType = None
            filenamedataid = dataid

    else:
        dataid = 'pal'
        aggType = None
        filenamedataid = dataid


start = pd.Timestamp(year, month, day).date()
end = start + pd.Timedelta(days=duration)

startlist = []
temp = pd.Timestamp(start.year, start.month, 1).date()
while temp < end:
    startlist.append(temp)
    temp += relativedelta(months=1)

startdate = []
for s in startlist:
    startdate.append(str(s.year) + '{:02d}'.format(s.month) + '{:02d}'.format(s.day))

if aggType is None:
    path = os.path.join('raw_data/NYISO', dataid)
else:
    path = os.path.join('raw_data/NYISO', dataid, aggType)

for s in startdate:
    params = {'dataid': dataid,
              'type': aggType,
              'startdate': s,
              'filenamedataid':filenamedataid,
              'path': path}

    if params['type'] is None:
        full_url = base_url + '/%s/%s%s_csv.zip' % (params['dataid'], s, params['filenamedataid'])
    else:
        full_url = base_url + '/%s/%s%s_%s_csv.zip' %(params['dataid'], s, params['filenamedataid'], params['type'])

    print('\nDownloading from...\n'
          '\n%s' % full_url)
    write_request(params)

merge(path, dataid, start, duration)

print('\nYour data has been successfully downloaded!\n'
      'Check your directory \'data/NYISO\'')
