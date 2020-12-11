import requests
import zipfile
import io
import os
import pandas as pd

path = os.path.join(os.getcwd(), 'data', 'MISO')

base_url = 'https://docs.misoenergy.org/marketreports/'

params = {'query_name': None,
          'date': None,
          'extension': None}


def write_request(params, type=None):
    if type == 'zip':
        filename = params['query_name'] + '_' + params['date'] + params['extension']
        full_url = base_url + filename
        r = requests.get(full_url)
        file = zipfile.ZipFile(io.BytesIO(r.content))
        file.extractall(path)
    elif type == 'csv':
        filename = params['date'] + '_' + params['query_name'] + params['extension']
        full_url = base_url + filename
        r = requests.get(full_url)
        data = r.content
        os.chdir(path)
        f = open(filename, 'wb')
        f.write(data)
        f.close()
