from lib.framework.CAISO.tool_utils import *


class Query(object):
    name = None
    report = '{http://www.caiso.com/soa/OASISReport_v1.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'version': 1}
        pdb.set_trace()
        return params

    def get_csv(self, start_date, end_date, step_size):
        csv_file_name = os.path.join(RAW_DIR, self.name) + '.csv'

        start_date = pd.to_datetime(start_date).tz_localize('US/Pacific')

        while start_date < pd.to_datetime(end_date).tz_localize('US/Pacific'):
            has_result = False
            params = self._build_request_params(start_date, step_size)
            while not has_result:
                xml_file_name = write_request(params)
                has_result = request_to_csv(os.path.join(XML_DIR, xml_file_name), csv_file_name, report=self.report)
                # time.sleep(6)
            start_date += datetime.timedelta(days=step_size)


# Prices reports. Inherit from Query
class LMP(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'grp_type': "ALL_APNODES",
                  'version': 1}

        return params


class DAM_LMP(LMP):
    name = 'PRC_LMP'
    market = 'DAM'


class HASP_LMP(LMP):
    name = 'PRC_HASP_LMP'
    market = 'HASP'


class RTPD_LMP(LMP):
    name = 'PRC_RTPD_LMP'
    market = 'RTPD'


class RTM_LMP(LMP):
    name = 'PRC_INTVL_LMP'
    market = 'RTM'


class SchedulingPointTie(Query):
    name = None
    market = None
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'grp_type': "ALL_APNODES",
                  'version': 4}

        return params


class DAM_SPTIE(SchedulingPointTie):
    name = 'PRC_SPTIE_LMP'
    market = 'DAM'


class RTPD_SPTIE(SchedulingPointTie):
    name = 'PRC_SPTIE_LMP'
    market = 'RTPD'


class RTD_SPTIE(SchedulingPointTie):
    name = 'PRC_SPTIE_LMP'
    market = 'RTD'


class AS(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'version': 1}

        return params


class DAM_AS(AS):
    name = 'PRC_AS'
    market = 'DAM'


class RTM_AS(AS):
    name = 'PRC_INTVL_AS'
    market = 'RTM'


class IntertieConstraintShadowPrice(Query):
    name = 'PRC_CNSTR'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'version': 1}

        return params


class FuelPrice(Query):
    name = 'PRC_FUEL'
    region = 'ALL'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'fuel_region_id': self.region,
                  'version': 1}

        return params


class GHG(Query):
    name = 'PRC_GHG_ALLOWANCE'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'version': 1}

        return params


# System Demand reports. Inherit from Query
class DemandForecast(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'version': 1}

        return params


class DAM_DF(DemandForecast):
    name = 'SLD_FCST'
    market = 'DAM'


class twoDayDA_DF(DemandForecast):
    name = 'SLD_FCST'
    market = '2DA'


class sevenDayDA_DF(DemandForecast):
    name = 'SLD_FCST'
    market = '7DA'


class RTM_DF(Query):
    name = 'SLD_FCST'
    market = 'RTM'
    exec_type = 'RTD'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'execution_type': self.exec_type,
                  'version': 1}

        return params


class AdvisoryDemandForecast(Query):
    name = 'SLD_ADV_FCST'
    market = 'RTPD'
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'version': 4}

        return params


# Energy reports. Inherit from Query
class SystemLoad(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'version': 1}

        return params


class DamSystemLoad(SystemLoad):
    name = 'ENE_SLRS'
    market = 'DAM'


class RucSystemLoad(SystemLoad):
    name = 'ENE_SLRS'
    market = 'RUC'


class HaspSystemLoad(SystemLoad):
    name = 'ENE_SLRS'
    market = 'HASP'


class RtmSystemLoad(SystemLoad):
    name = 'ENE_SLRS'
    market = 'RTM'


class DAM_MPM(Query):
    name = 'ENE_MPM'
    market = 'DAM'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'version': 1}

        return params


class HASP_MPM(Query):
    name = 'ENE_MPM'
    market = 'RTM'
    exec_type = 'HASP'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'execution_type': self.exec_type,
                  'version': 1}

        return params


class RTPD_MPM(Query):
    name = 'ENE_MPM'
    market = 'RTM'
    exec_type = 'RTPD'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'execution_type': self.exec_type,
                  'version': 1}

        return params


class FlexRampReq(Query):
    name = 'ENE_FLEX_RAMP_REQT'
    market = 'RTPD'
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'baa_grp_id': 'ALL',
                  'version': 4}

        return params


class FlexRampAggAward(Query):
    name = 'ENE_AGGR_FLEX_RAMP'
    market = 'RTPD'
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'baa_grp_id': 'ALL',
                  'version': 4}

        return params


class FlexRampDC(Query):
    name = 'ENE_FLEX_RAMP_DC'
    market = 'RTPD'
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'baa_grp_id': 'ALL',
                  'version': 4}

        return params


class EIMTransfer(Query):
    name = 'ENE_EIM_TRANSFER_TIE'
    market = 'ALL'
    report = '{http://www.caiso.com/soa/OASISReport_v4.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'baa_grp_id': 'ALL',
                  'version': 4}

        return params


class EIMTransferLimit(Query):
    name = 'ENE_EIM_TRANSFER_LIMITS_TIE'
    market = 'RTPD'
    report = '{http://www.caiso.com/soa/OASISReport_v5.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'baa_grp_id': 'ALL',
                  'version': 5}

        return params


class WindSolarSummary(Query):
    name = 'ENE_WIND_SOLAR_SUMMARY'
    report = '{http://www.caiso.com/soa/OASISReport_v5.xsd}'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'version': 5}

        return params


# Ancillary reports. Inherit from Query
class AS_REQ(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'anc_type': 'ALL',
                  'anc_region': 'ALL',
                  'version': 1}

        return params


class DAM_AS_REQ(AS_REQ):
    name = 'AS_REQ'
    market = 'DAM'


class HASP_AS_REQ(AS_REQ):
    name = 'AS_REQ'
    market = 'HASP'


class RTM_AS_REQ(AS_REQ):
    name = 'AS_REQ'
    market = 'RTM'


class AS_RES(Query):
    name = None
    market = None

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'market_run_id': self.market,
                  'anc_type': 'ALL',
                  'anc_region': 'ALL',
                  'version': 1}

        return params


class DAM_AS_RES(AS_RES):
    name = 'AS_RESULTS'
    market = 'DAM'


class HASP_AS_RES(AS_RES):
    name = 'AS_RESULTS'
    market = 'HASP'


class RTM_AS_RES(AS_RES):
    name = 'AS_RESULTS'
    market = 'RTM'


class AS_OpRes(Query):
    name = 'AS_OP_RSRV'

    def _build_request_params(self, start_date, duration):
        time_start, time_end = get_time_start_end(start_date, duration)
        params = {'startdatetime': time_start,
                  'enddatetime': time_end,
                  'queryname': self.name,
                  'version': 1}

        return params
