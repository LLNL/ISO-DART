# Import modules
import os
import webbrowser
from datetime import datetime, timedelta
import meteostat as met
from meteostat import units
from lib.framework.NSRDB.mainNSRDB import query_solar, write_user_config_file

# Set up output directories
data_dir = os.path.join(os.getcwd(), 'data', 'weather')
solar_dir = os.path.join(os.getcwd(), 'data', 'solar')

if os.path.isdir(data_dir):
    pass
else:
    os.makedirs(data_dir)

if os.path.isdir(solar_dir):
    pass
else:
    os.makedirs(solar_dir)

# Ask for desired dates
ind = 1
while ind == 1:
    print('\nPlease enter the start date and duration of the desired data set.')
    month = int(input('Month: '))
    day = int(input('Day: '))
    year = int(input('Year (4-digit format): '))
    try:
        datetime(year=year, month=month, day=day)
        ind = 0
    except:
        print('\nWARNING: The Date Does NOT Exist. Please Try Again!!')

duration = int(input('Duration (in days): '))

start = datetime(year, month, day)
end = datetime(year, month, day, 0, 0) + timedelta(days=duration)

# Ask for desired location
state = input('What state in the United States (use 2-letter code): ')
stations = met.Stations()
stations = stations.region('US', state.upper())
df = stations.fetch()

# We filter the stations so only stations with data available for the
# desired date range show up
stations_df = df[(df.daily_start <= start) & (df.daily_end >= end)]

# Show available stations for the desired dates
if len(stations_df) > 0:
    print('Please select one location from the following list '
          '(Answer 1 - {})'.format(len(stations_df)))
    for i in range(len(stations_df)):
        print('({}) {}'.format(str(i + 1), stations_df['name'][i]))
else:
    print('There are not weather stations available for the state and time range selected.')
    exit()

# Create geographical point with latitude, longitude and altitude
location_id = int(input('Location: '))

location_point = met.Point(stations_df['latitude'][location_id - 1],
                           stations_df['longitude'][location_id - 1],
                           stations_df['elevation'][location_id - 1])

# Query the hourly data for the specified location and time range
data = met.Hourly(location_point, start, end)
data = data.convert(units.imperial)
df = data.fetch()

# Rename dataframe columns for more self-explanatory column names
old_names = df.columns
new_names = ['temperature', 'dew_point', 'relative_humidity',
             'precipitation', 'snow_depth', 'wind_dir', 'wind_speed',
             'peak_wind_gust', 'air_pressure', 'sunshine',
             'weather_condition']
name_dict = dict(zip(old_names, new_names))
final_df = df.rename(columns=name_dict)

# Clean dataframe removing columns with no values
final_df.replace("", float('NaN'), inplace=True)
final_df.dropna(how='all', axis=1, inplace=True)

# If weather condition has data, replace with description string:
coco_dict = {1: 'Clear',
             2: 'Fair',
             3: 'Cloudy',
             4: 'Overcast',
             5: 'Fog',
             6: 'Freezing Fog',
             7: 'Light Rain',
             8: 'Rain',
             9: 'Heavy Rain',
             10: 'Freezing Rain',
             11: 'Heavy Freezing Rain',
             12: 'Sleet',
             13: 'Heavy Sleet',
             14: 'Light Snowfall',
             15: 'Snowfall',
             16: 'Heavy Snowfall',
             17: 'Rain Shower',
             18: 'Heavy Rain Shower',
             19: 'Sleet Shower',
             20: 'Heavy Sleet Shower',
             21: 'Snow Shower',
             22: 'Heavy Snow Shower',
             23: 'Lightning',
             24: 'Hail',
             25: 'Thunderstorm',
             26: 'Heavy Thunderstorm',
             27: 'Storm'}

if 'weather_condition' in final_df.columns:
    final_df.weather_condition.replace(coco_dict, inplace=True)

# Make sure we don't have any escape characters in the location name
station_name = stations_df['name'][location_id - 1]
if '/' in station_name:
    station_name = station_name.replace('/', '-')

# Save final dataset
final_df.to_csv(os.path.join(data_dir,
                             '{start}_to_{end}_{station}_{state}.csv'.format(start=start.date(),
                                                                             end=end.date(),
                                                                             station=station_name,
                                                                             state=state.upper())))

print('\nYour weather data has been successfully downloaded!\n'
      'Check your directory {}'.format(data_dir))

# Ask about solar data
solar_data = input('\nDo you want to get solar data from NSRDB? (y/n): ')
if solar_data.lower() == 'y':
    if os.path.isfile('user_config.ini'):
        user_config_file = 'user_config.ini'
    else:
        print('You need to request an API key from the following link:\n'
              'https://developer.nrel.gov/signup/')
        open_url = input('Do you want to open the link now? (y/n): ')
        if open_url.lower() == 'y':
            webbrowser.open('https://developer.nrel.gov/signup/')
            api_key = input('API key: ')
            first_name = input('First name: ')
            last_name = input('Last name: ')
            affiliation = input('Affiliation: ')
            email = input('Email address: ')
            user_config_file = write_user_config_file(api_key, first_name, last_name, affiliation, email)
        else:
            print("\nSolar data will not be downloaded until you get an API key.")

    solar_df = query_solar(stations_df['latitude'][location_id - 1],
                           stations_df['longitude'][location_id - 1],
                           year,
                           user_config_file)

    solar_df.to_csv(os.path.join(solar_dir,
                                 'solar_data_{year}_{station}_{state}.csv'.format(year=year,
                                                                                  station=station_name,
                                                                                  state=state.upper())))

    print('\nYour solar data has been successfully downloaded!\n'
          'Check your directory {}'.format(solar_dir))
