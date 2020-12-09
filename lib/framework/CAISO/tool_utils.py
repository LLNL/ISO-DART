import requests
import xml.etree.ElementTree as ET
import csv
import zipfile
import pdb
import io
import os
import datetime
import time
import pandas as pd
import sys

URL = 'http://oasis.caiso.com/oasisapi/SingleZip'
QUERY_DATE_FORMAT = '%Y%m%dT%H:%M-0000'
DATA_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S-00:00'

DATA_DIR = os.path.join(os.getcwd(), 'data')
RAW_DIR = os.path.join(os.getcwd(), 'raw_data')
XML_DIR = os.path.join(os.getcwd(), 'raw_data', 'xml_files')


def write_request(params):
    # Perform request
    r = requests.get(URL, params=params, stream=True, verify=True)
    print(r.url)
    # If request is successful
    if r.ok:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        for src_file_name in z.namelist():
            dst_file_name = '_'.join(src_file_name.split('_')[0:2]) + '_' + params["queryname"] + '.xml'
            fout = open(os.path.join(XML_DIR, dst_file_name), 'wb')
            fout.write(z.read(src_file_name))
            fout.close()
        readXml = str(z.read(src_file_name))
        try:
            errCode = readXml.split('<m:ERR_CODE>')[1].split('</m:ERR_CODE>')[0]
            errMessage = readXml.split('<m:ERR_DESC>')[1].split('</m:ERR_DESC>')[0]
            print("WARNING!! ERROR CODE:" + errCode + "\t"+ errMessage + "\nProgram End!! Please Try Again.")
            errDetector = 1
        except:
            errDetector = 0
            pass
        if errDetector == 1:
            sys.exit()
    else:
        print(r.text)
        print("WARNING: Request failed!!! with:")
        print(r.url)

    return dst_file_name


def request_to_csv(xml_file_name, csv_file_name, report='{http://www.caiso.com/soa/OASISReport_v1.xsd}'):
    caiso_report = report

    # Parse the xml file
    tree = ET.parse(xml_file_name)
    root = tree.getroot()

    # Open the csv file for writing, appending if it already exists
    if os.path.isfile(csv_file_name):
        build_header = False
        csv_handle = open(csv_file_name, 'a')
    else:
        build_header = True
        csv_handle = open(csv_file_name, 'w')

    csv_writer = csv.writer(csv_handle)

    header = []

    try:
        if root[1][0][2][0].tag == caiso_report + 'ERR_CODE':
            error_code = root[1][0][2][0].text
            print(error_code)
            return False
    except IndexError:
        pass

    for report in root.iter(caiso_report + 'REPORT_DATA'):
        if build_header:
            for col in report:
                header.append(col.tag.replace(caiso_report, ""))
            csv_writer.writerow(header)
            build_header = False
        row = []
        for col in report:
            row.append(col.text)
        csv_writer.writerow(row)
    csv_handle.close()

    return True


def get_time_start_end(start_date, duration):
    end_date = start_date + datetime.timedelta(days=duration)
    time_start = start_date.tz_convert('UTC').strftime(QUERY_DATE_FORMAT)
    time_end = end_date.tz_convert('UTC').strftime(QUERY_DATE_FORMAT)
    return time_start, time_end


def merge_csv(query_name, date_col):
    # Run this from the python prompt to merge all of the annual files
    # With date_col as the index column of the date time (i.e., 4 or 5)
    # Index should identify the interval end.
    # For prices it is index 5
    # For load forecast it is index 5,
    # For renewable forecasts it's index 4
    dst_file_name = DATA_DIR % query_name + '.csv'

    # Open the dest file for writing, appending if it already exists
    build_header = True
    dst_handle = open(dst_file_name, 'w')
    dst_writer = csv.writer(dst_handle)

    for year in ['2013', '2014', '2015', '2016', '2017']:
        src_file_name = os.path.join(RAW_DIR, query_name) + '_' + year + '.csv'
        src_handle = open(src_file_name, 'rb')
        src_reader = csv.reader(src_handle)

        header = next(src_reader)
        if build_header:
            dst_writer.writerow(header)
            build_header = False

        year = int(year)
        for row in src_reader:
            if pd.to_datetime(row[date_col], format=DATA_DATE_FORMAT).tz_localize('UTC').tz_convert(
                    'US/Pacific').year == year:
                dst_writer.writerow(row)
        src_handle.close()

    dst_handle.close()


def order_separate_csv(query_name, market=None):
    df = pd.read_csv(os.path.join(RAW_DIR, '%s.csv' % query_name))
    if query_name == 'ENE_WIND_SOLAR_SUMMARY':
        sorted_df = df.sort_values(['OPR_DATE'])
    else:
        sorted_df = df.sort_values(['OPR_DATE', 'INTERVAL_NUM'])

    os.remove(os.path.join(RAW_DIR, '%s.csv' % query_name))
    start = min(df.OPR_DATE)
    end = max(df.OPR_DATE)

    items = []
    for item in df.DATA_ITEM:
        if item not in items:
            items.append(item)

    os.chdir(os.path.join(DATA_DIR, 'CAISO'))

    for item in items:
        temp_df = sorted_df[sorted_df['DATA_ITEM'] == item]
        if market is None:
            temp_df.to_csv('%s_to_%s_%s_%s.csv' % (start, end, query_name, item), index=False)
        else:
            temp_df.to_csv('%s_to_%s_%s_%s_%s.csv' % (start, end, market, query_name, item), index=False)


def copy_csv(query_name):
    df = pd.read_csv(os.path.join(RAW_DIR, '%s.csv' % query_name))
    os.remove(os.path.join(RAW_DIR, '%s.csv' % query_name))

    start = min(df.OPR_DATE)
    end = max(df.OPR_DATE)

    os.chdir(os.path.join(DATA_DIR, 'CAISO'))

    df.to_csv('%s_to_%s_%s.csv' % (start, end, query_name), index=False)
