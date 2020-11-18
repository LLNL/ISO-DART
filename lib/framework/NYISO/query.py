import requests
import zipfile
import io

base_url = 'http://mis.nyiso.com/public/csv'
params = {'dataid': None,
          'type': None,
          'startdate': None,
          'filenamedataid': None,
          'path': None}


def write_request(params):
    date = params['startdate'][0:-2] + '01'  # first date of the month of the day being requested

    if params['type'] is None:
        full_url = base_url + '/%s/%s%s_csv.zip' % (params['dataid'], date, params['filenamedataid'])
    else:
        full_url = base_url + '/%s/%s%s_%s_csv.zip' %(params['dataid'], date, params['filenamedataid'], params['type'])

    r = requests.get(full_url)
    file = zipfile.ZipFile(io.BytesIO(r.content))
    file.extractall(path=params['path'])
