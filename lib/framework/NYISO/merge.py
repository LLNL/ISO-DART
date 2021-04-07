import os
import pandas as pd
from dateutil.relativedelta import relativedelta


def merge(path, dataid, start, duration):
    destination = os.path.join(os.getcwd(), 'data', 'NYISO')
    files = os.listdir(path)
    files.sort()

    date_list = []
    for d in range(duration):
        date = start + relativedelta(days=d)
        datestring = str(date.year) + '{:02d}'.format(date.month) + '{:02d}'.format(date.day)
        date_list.append(datestring)

    selected_files = []
    for f in files:
        if f[0:8] in date_list:
            selected_files.append(f)

    if len(selected_files[0].split('_')) > 1:
        suffix = selected_files[0].split('_')[-1].split('.')[0]
    else:
        suffix = ''

    combined_csv = pd.concat([pd.read_csv(os.path.join(path, f)) for f in selected_files])
    os.chdir(destination)
    if len(suffix) > 0:
        combined_csv.to_csv('{}_to_{}_{}_{}.csv'.format(date_list[0], date_list[-1], dataid, suffix), index=False)

    else:
        combined_csv.to_csv('{}_to_{}_{}.csv'.format(date_list[0], date_list[-1], dataid), index=False)
