from lib.framework.MISO.query import *
import datetime

data_dir = os.path.join(os.getcwd(), 'data', 'MISO')
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

start = pd.Timestamp(year, month, day).date()

end = start + pd.Timedelta(days=duration)

datelist = []
while start < end:
    datelist.append(start)
    start += pd.Timedelta(days=1)

date = []
for d in datelist:
    date.append(str(d.year) + '{:02d}'.format(d.month) + '{:02d}'.format(d.day))


data_type = int(input('\nWhat type of data? (Answer 1, 2, or 3)\n'
                      '(1) Historical Locational Marginal Prices (LMP)\n'
                      '(2) Historical Marginal Clearing Prices (MCP)\n'
                      '(3) Summary Reports\n'))

if data_type == 1:
    lmp = int(input('\nWhat type of LMP? (Answer 1, 2, 3, 4, 5, or 6)\n'
                    '(1) Day-Ahead EPNode LMPs\n'
                    '(2) Day-Ahead Market ExAnte LMPs\n'
                    '(3) Day-Ahead Market ExPost LMPs\n'
                    '(4) Real-Time EPNode LMPs\n'
                    '(5) Real-Time 5-min ExAnte LMPs\n'
                    '(6) Real-Time Final Market LMPs\n'))

    if lmp == 1:
        query_name = 'DA_Load_EPNodes'
        extension = '.zip'
        fileType = 'zip'

    elif lmp == 2:
        query_name = 'da_exante_lmp'
        extension = '.csv'
        fileType = 'csv'

    elif lmp == 3:
        query_name = 'da_expost_lmp'
        extension = '.csv'
        fileType = 'csv'

    elif lmp == 4:
        query_name = 'RT_Load_EPNodes'
        extension = '.zip'
        fileType = 'zip'

    elif lmp == 5:
        query_name = '5min_exante_lmp'
        extension = '.xls'
        fileType = 'csv'

    elif lmp == 6:
        query_name = 'rt_lmp_final'
        extension = '.csv'
        fileType = 'csv'

elif data_type == 2:
    mcp = int(input('\nWhat type of MCP? (Answer 1, 2, 3, 4, 5, or 6)\n'
                    '(1) ASM Day-Ahead Market ExAnte MCPs\n'
                    '(2) ASM Day-Ahead Market ExPost MCPs\n'
                    '(3) ASM Real-Time 5-min ExAnte MCPs\n'
                    '(4) ASM Real-Time Final Market MCPs\n'
                    '(5) Day-Ahead ExAnte Ramp MCPs\n'
                    '(6) Day-Ahead ExPost Ramp MCPs\n'))

    if mcp == 1:
        query_name = 'asm_exante_damcp'
        extension = '.csv'
        fileType = 'csv'

    elif mcp == 2:
        query_name = 'asm_expost_damcp'
        extension = '.csv'
        fileType = 'csv'

    elif mcp == 3:
        query_name = '5min_exante_mcp'
        extension = '.xls'
        fileType = 'csv'

    elif mcp == 4:
        query_name = 'asm_rtmcp_final'
        extension = '.csv'
        fileType = 'csv'

    elif mcp == 5:
        query_name = 'da_exante_ramp_mcp'
        extension = '.xls'
        fileType = 'csv'

    elif mcp == 6:
        query_name = 'da_expost_ramp_mcp'
        extension = '.xls'
        fileType = 'csv'

elif data_type == 3:
    summary = int(input('\nWhat type of summary? (Answer 1 or 2)\n'
                        '(1) Daily Forecast and Actual Load by Local Resource Zone\n'
                        '(2) Daily Regional Forecast and Actual Load\n'))

    if summary == 1:
        query_name = 'df_al'
        extension = '.xls'
        fileType = 'csv'

    elif summary == 2:
        query_name = 'rf_al'
        extension = '.xls'
        fileType = 'csv'


print('\nDownloading...\n')
for d in date:
    params = {'query_name': query_name,
              'date': d,
              'extension': extension}

    write_request(params, type=fileType)

print('\nYour data has been successfully downloaded!\n'
      'Check your directory \'data/MISO\'\n')
