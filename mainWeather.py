# Import modules
import os
from datetime import datetime, timedelta
import meteostat as met
from meteostat import units

# Set up output directory
data_dir = os.path.join(os.getcwd(), 'data', 'weather')

if os.path.isdir(data_dir):
    pass
else:
    os.makedirs(data_dir)

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
new_names = ['temperature', 'dew_point', 'relative_humidty',
             'precipitation', 'snow_depth', 'wind_dir', 'wind_speed',
             'peak_wind_gust', 'air_pressure', 'sunshine',
             'weather_condition_code']
name_dict = dict(zip(old_names, new_names))
final_df = df.rename(columns=name_dict)

# Clean dataframe removing columns with no values
final_df.replace("", float('NaN'), inplace=True)
final_df.dropna(how='all', axis=1, inplace=True)

# Make sure we don't have any escape characters in the location name
station_name = stations_df['name'][location_id - 1]
if '/' in station_name:
    station_name = station_name.replace(' / ', '-')

# Save final dataset
final_df.to_csv(os.path.join(data_dir, '{}_to_{}_{}_{}.csv'.format(start.date(),
                                                                   end.date(),
                                                                   station_name,
                                                                   state.upper())))

print('\nYour data has been successfully downloaded!\n'
      'Check your directory {}'.format(data_dir))
