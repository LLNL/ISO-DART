# ISO-DART v1.0.0
## Release:  LLNL-CODE-815334
This code was developed by Pedro Sotorrio at Lawrence Livermore National Laboratory.

THIS CODE IS COVERED BY THE MIT SOFTWARE LICENSE. SEE INCLUDED FILE, MIT.pdf FOR DETAILS.

Copyright (c) 2020, Lawrence Livermore National Security, LLC. All rights reserved.
LLNL-CODE-815334

NOTICE

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under contract no. DE-AC52-07NA27344 
(Contract 44) between the U.S. Department of Energy (DOE) and Lawrence Livermore National Security, LLC (LLNS) for the 
operation of LLNL.  Copyright is reserved to Lawrence Livermore National Security, LLC for purposes of controlled 
dissemination, commercialization through formal licensing, or other disposition under terms of Contract 44; DOE 
policies, regulations and orders; and U.S. statutes.  The rights of the Federal Government are reserved under 
Contract 44.

DISCLAIMER

This work was prepared as an account of work sponsored by an agency of the United States Government.

NEITHER THE UNITED STATES GOVERNMENT NOR LAWRENCE LIVERMORE NATIONAL SECURITY, LLC NOR ANY OF THEIR EMPLOYEES, MAKES ANY 
WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS, OR USEFULNESS 
OF ANY INFORMATION, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD NOT INFRINGE 
PRIVATELY-OWNED RIGHTS.  THIS SOFTWARE IS PROVIDED BY LAWRENCE LIVERMORE NATIONAL SECURITY, LLC "AS IS" AND ANY EXPRESS 
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY 
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Reference herein to any specific commercial products, process, or service by trade name, trademark, manufacturer or 
otherwise does not necessarily constitute or imply its endorsement, recommendation, or favoring by the United States 
Government or Lawrence Livermore National Security, LLC. The views and opinions of authors expressed herein do not 
necessarily state or reflect those of the United States Government or Lawrence Livermore National Security, LLC, and 
shall not be used for advertising or product endorsement purposes.

LICENSE

Any use, reproduction, modification, or distribution of this software or documentation requires a license from Lawrence 
Livermore National Security, LLC. Contact: Lawrence Livermore National Laboratory, Industrial Partnerships Office, P.O. 
Box 808, L-795, Livermore, CA 94551. www.llnl.gov Neither the name of LLNS nor the names of its contributors may be used 
to endorse or promote products derived from this software without specific prior written permission.

MIT.pdf:

Copyright 2020 Lawrence Livermore National Security, LLC.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
documentation files (the "Software"), to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the 
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.



# ISO-DART: Independent System Operator Data Automated Request Tool

## Introduction
Very early stages of a simple tool able to create multiple automated requests of different ISO data. 
Currently supporting:
* California Independent System Operator (CAISO).
* Midcontinent Independent System Operator (MISO).
* New York Independent System Operator (NYISO).

## Authors
* Thomas Edmunds, Lawrence Livermore National Laboratory.
* Amelia Musselman, Lawrence Livermore National Laboratory.
* Pedro Sotorrio, Lawrence Livermore National Laboratory.
* Chih-Che Sun, Lawrence Livermore National Laboratory.

## System Requirements and Installation
These are very basic instructions so any type of user can get ISO-DART up and running in their machines. More advance 
users can skip the appropriate steps.

1. Install [Git](https://git-scm.com/).
2. Install [Anaconda](https://anaconda.com/).

Once Git and Anaconda are installed, in a terminal run the following commands:

```
git clone https://github.com/LLNL/ISO-DART.git  # Clone ISO-DART GitHub repository
cd iso-dart  # Change to iso-dart directory
conda create --name iso-dart python=3.8  # Create iso-dart Anaconda environment
conda activate iso-dart  # Activate iso-dart environment
pip install -r requirements.txt  # Install required packages
```

## Usage
The tool as of now is very rudimentary, and it works as a simple command line script where the user answers
a few questions regarding the type of data (ISO or weather data), the specific ISO or weather station, start date, 
and end date for the desired dataset. 

In the command line just run the following command: `python ISODART.py`

## Weather Module
The weather module uses the [Meteostat](https://dev.meteostat.net/) python library. Although documentation can
be found online, below you can find a description of the columns you will get in your dataset:

| Column                 | Description                                  | Type       |
| ---------------------- | -------------------------------------------- | ---------- |
| time                   | The datetime of the observation              | Datetime64 |
| temperature            | The air temperature in *ºF*                  | Float64    |
| dew_point              | The dew point in *ºF*                        | Float64    |
| relative_humidity      | The relative humidity in percent (*%*)       | Float64    |
| precipitation          | The one hour precipitation total in *inches* | Float64    |
| snow_depth             | The snow depth in *inches*                   | Float64    |
| wind_dir               | The average wind direction in degrees (*º*)  | Float64    |
| wind_speed             | The average wind speed in *mph*              | Float64    |
| wind_peak_gust         | The peak wind gust in *mph*                  | Float64    |
| air_pressure           | The average sea-level air pressure in *hPa*  | Float64    |
| sunshine               | The one hour sunshine total in *min*         | Float64    |
| weather_condition      | The weather condition description            | String     |


        NOTE: Keep in mind some of these columns will not show up in the final dataset because the program 
        will drop those columns where all values are null. 

### National Solar Radiation Database ([NSRDB](https://nsrdb.nrel.gov/)) API
Within the weather module, the user has the opportunity to download solar data for the same location they downloaded 
weather data previously. 

The first the user decides to use this capability, they will be guided on how to get an API token and provide it to the 
program. ISO-DART will save that information in a configuration file, so the user doesn't have to go through the same 
process ever again. 