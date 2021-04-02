import shutil
from lib.framework.CAISO.query import *
import datetime

raw_dir = os.path.join(os.getcwd(), 'raw_data')
xml_dir = os.path.join(os.getcwd(), 'raw_data', 'xml_files')
data_dir = os.path.join(os.getcwd(), 'data', 'CAISO')

if os.path.isdir(raw_dir):
    pass
else:
    os.makedirs(raw_dir)

if os.path.isdir(xml_dir):
    pass
else:
    os.makedirs(xml_dir)

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
step_size = 1  # in days

data_type = int(input('\nWhat type of data? (Answer 1, 2, 3, or 4)\n'
                      '(1) Pricing Data\n'
                      '(2) System Demand Data\n'
                      '(3) Energy Data\n'
                      '(4) Ancillary Services (AS) Data\n'))

if data_type == 1:
    price = int(input('\nWhat type of pricing data? (Answer 1, 2, 3, 4, or 5)\n'
                      '(1) Locational Marginal Prices (LMP)\n'
                      '(2) Ancillary Services (AS) Clearing Prices\n'
                      '(3) Intertie Constraint Shadow Prices\n'
                      '(4) Fuel Prices\n'
                      '(5) Green House Gas (GHG) Allowance Prices\n'))

    if price == 1:
        market = int(input('\nWhich energy market? (Answer 1, 2, 3, or 4)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Hour-Ahead Scheduling Process (HASP)\n'
                           '(3) Real-Time Market (RTM)\n'
                           '(4) Real-Time Pricing Day (RTPD)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_LMP().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_LMP.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            HASP_LMP().get_csv(start, end, step_size=step_size)
            order_separate_csv(HASP_LMP.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 3:
            print('\nDownloading from...\n')
            RTM_LMP().get_csv(start, end, step_size=step_size)
            order_separate_csv(RTM_LMP.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 4:
            print('\nDownloading from...\n')
            RTPD_LMP().get_csv(start, end, step_size=step_size)
            order_separate_csv(RTPD_LMP.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

    elif price == 2:
        market = int(input('\nWhich energy market? (Answer 1 or 2)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Real-Time Market (RTM)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_AS().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_AS.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            RTM_AS().get_csv(start, end, step_size=step_size)
            order_separate_csv(RTM_AS.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

    elif price == 3:
        print('\nDownloading from...\n')
        IntertieConstraintShadowPrice().get_csv(start, end, step_size=step_size)
        order_separate_csv(IntertieConstraintShadowPrice.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif price == 4:
        print('\nDownloading from...\n')
        FuelPrice().get_csv(start, end, step_size=step_size)
        copy_csv(FuelPrice.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif price == 5:
        print('\nDownloading from...\n')
        GHG().get_csv(start, end, step_size=step_size)
        copy_csv(GHG.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')


elif data_type == 2:
    system_demand = int(input('\nWhat type of system demand data? (Answer 1 or 2)\n'
                              '(1) CAISO Demand Forecast\n'
                              '(2) Advisory CAISO Demand Forecast\n'))

    if system_demand == 1:
        market = int(input('\nWhich energy market? (Answer 1, 2, 3, or 4)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Two Day-Ahead Market (2DA)\n'
                           '(3) Seven Day-Ahead Market (7DA)\n'
                           '(4) Real-Time Market (RTM)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_DF().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_DF.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            twoDayDA_DF().get_csv(start, end, step_size=step_size)
            order_separate_csv(twoDayDA_DF.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 3:
            print('\nDownloading from...\n')
            sevenDayDA_DF().get_csv(start, end, step_size=step_size)
            order_separate_csv(sevenDayDA_DF.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 4:
            print('\nDownloading from...\n')
            RTM_DF().get_csv(start, end, step_size=step_size)
            order_separate_csv(RTM_DF.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

    elif system_demand == 2:
        print('\nDownloading from...\n')
        AdvisoryDemandForecast().get_csv(start, end, step_size=step_size)
        try:
            order_separate_csv(AdvisoryDemandForecast.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')
        except:
            print("There is no data available to return.")


elif data_type == 3:
    load = int(input('\nWhat type of energy data? (Answer 1, 2, 3, 4, 5, 6, 7, or 8)\n'
                     '(1) Market Power Mitigation (MPM) Status\n'
                     '(2) Flexible Ramp Requirements\n'
                     '(3) Flexible Ramp Aggregated Awards\n'
                     '(4) Flexible Ramp Surplus Demand Curves (DC)\n'
                     '(5) EIM Transfer\n'
                     '(6) EIM Transfer Limits\n'
                     '(7) Wind and Solar Summary\n'
                     '(8) System Load and Resource Schedules\n'))

    if load == 1:
        market = int(input('\nWhich energy market? (Answer 1 or 2)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Hour-Ahead Scheduling Process (HASP)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_MPM().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_MPM.name, market=DAM_MPM.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            HASP_MPM().get_csv(start, end, step_size=step_size)
            order_separate_csv(HASP_MPM.name, market=HASP_MPM.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

    elif load == 2:
        print('\nDownloading from...\n')
        FlexRampReq().get_csv(start, end, step_size=step_size)
        src = os.path.join(RAW_DIR, '{}.csv'.format(FlexRampReq.name))
        dst = os.path.join(DATA_DIR, 'CAISO', '{}_to_{}_{}.csv'.format(start, end, FlexRampReq.name))
        shutil.copyfile(src, dst)
        os.remove(src)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 3:
        print('\nDownloading from...\n')
        FlexRampAggAward().get_csv(start, end, step_size=step_size)
        src = os.path.join(RAW_DIR, '{}.csv'.format(FlexRampAggAward.name))
        dst = os.path.join(DATA_DIR, 'CAISO', '{}_to_{}_{}.csv'.format(start, end, FlexRampAggAward.name))
        shutil.copyfile(src, dst)
        os.remove(src)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 4:
        print('\nDownloading from...\n')
        FlexRampDC().get_csv(start, end, step_size=step_size)
        src = os.path.join(RAW_DIR, '{}.csv'.format(FlexRampDC.name))
        dst = os.path.join(DATA_DIR, 'CAISO', '{}_to_{}_{}.csv'.format(start, end, FlexRampDC.name))
        shutil.copyfile(src, dst)
        os.remove(src)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 5:
        print('\nDownloading from...\n')
        EIMTransfer().get_csv(start, end, step_size=step_size)
        src = os.path.join(RAW_DIR, '{}.csv'.format(EIMTransfer.name))
        dst = os.path.join(DATA_DIR, 'CAISO', '{}_to_{}_{}.csv'.format(start, end, EIMTransfer.name))
        shutil.copyfile(src, dst)
        os.remove(src)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 6:
        print('\nDownloading from...\n')
        EIMTransferLimit().get_csv(start, end, step_size=step_size)
        order_separate_csv(EIMTransferLimit.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 7:
        print('\nDownloading from...\n')
        WindSolarSummary().get_csv(start, end, step_size=step_size)
        order_separate_csv(WindSolarSummary.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

    elif load == 8:
        market = int(input('\nWhich energy market? (Answer 1, 2, 3, or 4)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Residual Unit Commitment (RUC)\n'
                           '(3) Hour-Ahead Scheduling Process (HASP)\n'
                           '(4) Real-Time Market (RTM)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DamSystemLoad().get_csv(start, end, step_size=step_size)
            order_separate_csv(DamSystemLoad.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            RucSystemLoad().get_csv(start, end, step_size=step_size)
            order_separate_csv(RucSystemLoad.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 3:
            print('\nDownloading from...\n')
            HaspSystemLoad().get_csv(start, end, step_size=step_size)
            order_separate_csv(HaspSystemLoad.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 4:
            print('\nDownloading from...\n')
            RtmSystemLoad().get_csv(start, end, step_size=step_size)
            order_separate_csv(RtmSystemLoad.name)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

elif data_type == 4:
    ancillary = int(input('\nWhat type of ancillary services data? (Answer 1, 2, or 3)\n'
                          '(1) Ancillary Services (AS) Requirements\n'
                          '(2) Ancillary Services (AS) Results\n'
                          '(3) Actual Operating Reserves\n'))

    if ancillary == 1:
        market = int(input('\nWhich energy market? (Answer 1, 2, or 3)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Hour-Ahead Scheduling Process (HASP)\n'
                           '(3) Real-Time Market (RTM)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_AS_REQ().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_AS_REQ.name, market=DAM_AS_REQ.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            HASP_AS_REQ().get_csv(start, end, step_size=step_size)
            order_separate_csv(HASP_AS_REQ.name, market=HASP_AS_REQ.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 3:
            print('\nDownloading from...\n')
            RTM_AS_REQ().get_csv(start, end, step_size=step_size)
            try:
                order_separate_csv(RTM_AS_REQ.name, market=RTM_AS_REQ.market)
                print('\nYour data has been successfully downloaded!\n'
                      'Check your directory \'data/CAISO\'\n')
            except:
                print('There is no data available to return.')

    elif ancillary == 2:
        market = int(input('\nWhich energy market? (Answer 1, 2, or 3)\n'
                           '(1) Day-Ahead Market (DAM)\n'
                           '(2) Hour-Ahead Scheduling Process (HASP)\n'
                           '(3) Real-Time Market (RTM)\n'))

        if market == 1:
            print('\nDownloading from...\n')
            DAM_AS_RES().get_csv(start, end, step_size=step_size)
            order_separate_csv(DAM_AS_RES.name, market=DAM_AS_RES.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 2:
            print('\nDownloading from...\n')
            HASP_AS_RES().get_csv(start, end, step_size=step_size)
            order_separate_csv(HASP_AS_RES.name, market=HASP_AS_RES.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

        elif market == 3:
            print('\nDownloading from...\n')
            RTM_AS_RES().get_csv(start, end, step_size=step_size)
            order_separate_csv(RTM_AS_RES.name, market=RTM_AS_RES.market)
            print('\nYour data has been successfully downloaded!\n'
                  'Check your directory \'data/CAISO\'\n')

    elif ancillary == 3:
        print('\nDownloading from...\n')
        AS_OpRes().get_csv(start, end, step_size=step_size)
        order_separate_csv(AS_OpRes.name)
        print('\nYour data has been successfully downloaded!\n'
              'Check your directory \'data/CAISO\'\n')

shutil.rmtree(raw_dir)
