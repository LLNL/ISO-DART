import os
import configparser
import pandas as pd


def write_user_config_file(api_key, first_name, last_name, affiliation, email):
    outdir = os.getcwd()
    user_config_file = os.path.join(outdir, 'user_config.ini')
    f = open(user_config_file, 'w')
    # API
    f.write('[API]\n')
    f.write('api_key = {key}\n'.format(key=api_key))
    f.write('[USER_INFO]\n')
    f.write('first_name = {first}\n'.format(first=first_name))
    f.write('last_name = {last}\n'.format(last=last_name))
    f.write('affiliation = {affiliation}\n'.format(affiliation=affiliation))
    f.write('email = {email}\n'.format(email=email))
    f.close()
    return user_config_file


def query_solar(lat, lon, year, user_config_file):
    # read from user_config_file
    user_config = configparser.ConfigParser(allow_no_value=True)
    user_config.read(user_config_file)
    api_key = user_config['API']['api_key']
    first_name = user_config['USER_INFO']['first_name']
    last_name = user_config['USER_INFO']['last_name']
    affiliation = user_config['USER_INFO']['affiliation']
    email = user_config['USER_INFO']['email']

    # Set the attributes to extract (e.g., dhi, ghi, etc.), separated by commas.
    attributes = 'ghi,dhi,dni,solar_zenith_angle'
    year = str(year)
    leap_year = 'true'
    interval = '60'
    utc = 'false'
    # Your full name, use '+' instead of spaces.
    your_name = '{first}+{last}'.format(first=first_name, last=last_name)
    reason_for_use = ''
    mailing_list = 'false'

    # Declare url string
    url = 'https://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv?wkt=POINT({lon}%20{lat})&' \
          'names={year}&leap_day={leap}&interval={interval}&utc={utc}&full_name={name}&email={email}&' \
          'affiliation={affiliation}&mailing_list={mailing_list}&reason={reason}&' \
          'api_key={api}&attributes={attr}'.format(year=year, lat=lat, lon=lon, leap=leap_year,
                                                   interval=interval, utc=utc, name=your_name,
                                                   email=email, mailing_list=mailing_list,
                                                   affiliation=affiliation, reason=reason_for_use,
                                                   api=api_key, attr=attributes)

    # Return all but first 2 lines of csv to get data:
    try:
        solar_df = pd.read_csv(url, skiprows=2)
        # Set the time index in the pandas dataframe:
        if (int(year) % 4) == 0:
            if (int(year) % 100) == 0:
                if (int(year) % 400) == 0:
                    min_in_year = 527040
                else:
                    min_in_year = 525600
            else:
                min_in_year = 527040
        else:
            min_in_year = 525600

        solar_df = solar_df.set_index(pd.date_range('1/1/{yr}'.format(yr=year),
                                                    freq=interval + 'Min',
                                                    periods=min_in_year / int(interval)))

    except Exception as e:
        print(e)

    return solar_df
