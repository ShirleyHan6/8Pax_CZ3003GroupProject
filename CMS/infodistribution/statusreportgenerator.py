from .informationsender import InformationSender
from utilities.incidenttype import IncidentType
from utilities.incidentstatus import IncidentStatus
from utilities.region import Region
from callcentre.models import Incident
from threading import Timer
from datetime import datetime


class StatusReportGenerator:
    """
    Generates status reports for the prime minister containing key indicators
    and trends (calculated from the key indicators of the previous report).

    interval: indicates how often status reports are generated.
    """

    def __init__(self, interval):
        self.messages_received = 0
        self.distributor = InformationSender()
        self.interval = interval
        self.prime_minister_address = 'lee.hsien.loong@gmail.com'
        self.prev_key_indicators = KeyIndicators()
        self.key_indicators = KeyIndicators()

        Timer(interval, self.generate_report).start()  # Schedule first report

    def notify(self, message):
        """
        Updates key indicators according to the incident update contained in the given message.
        """
        self.messages_received += 1
        incident = Incident.objects.get(pk=message.incident_id)
        incident_type = IncidentType.from_str(incident.incident_category)
        region = Region.from_str(incident.incident_region)

        if message.incident_status == IncidentStatus.NEW:
            self.key_indicators.reported_incidents[incident_type] += 1
            self.key_indicators.affected_regions[region] += 1
        elif message.incident_status == IncidentStatus.RESOLVED:
            self.key_indicators.total_resolution_time +=\
                datetime.now() - incident.incident_time
            self.key_indicators.resolved_incidents += 1

    def generate_report(self):
        """
        Generates a status report based on key indicators, sends it by email to the prime minister and
        resets key indicators.
        """
        # Schedule next report
        Timer(self.interval, self.generate_report).start()

        title = 'Incident Status Report ' + str(datetime.now())
        report = self.key_indicators.reported_incidents_by_type() + '\n'
        report += self.key_indicators.ongoing_incidents() + '\n'
        report += self.key_indicators.mean_resolution_time() + '\n'
        report += self.key_indicators.trending_incident_type(self.prev_key_indicators) + '\n'
        report += self.key_indicators.trending_region(self.prev_key_indicators)

        self.distributor.send_email(title, report, self.prime_minister_address)

        # Reset key indicators
        self.prev_key_indicators = self.key_indicators
        self.key_indicators = KeyIndicators()


class KeyIndicators:
    """
    Contains statistics used to calculate key indicators and trends.
    Can calculate the indicators and trends, which are returned as human-readable strings.
    """
    def __init__(self):
        self.reported_incidents = {key: 0 for key in IncidentType}
        self.affected_regions = {key: 0 for key in Region}
        self.resolved_incidents = 0
        self.total_resolution_time = 0.0

    def reported_incidents_by_type(self):
        """
        Calculates the number of incidents reported of each type.
        """
        res = 'Number of reported incidents of type'
        for tag in IncidentType:
            res += '\n\t- ' + tag.value + ': ' + self.reported_incidents[tag] + '.'

    def ongoing_incidents(self):
        """
        Calculates the number of incidents which have not yet been resolved.
        """
        ongoing = sum(self.reported_incidents.values()) - self.resolved_incidents
        return 'Number of incidents which are still ongoing: ' + str(ongoing) + '.'

    def mean_resolution_time(self):
        """
        Calculates the mean time for an incident to become resolved.
        """
        mtr = self.total_resolution_time / self.resolved_incidents
        return 'Mean time of incident resolution: ' + str(mtr) + '.'

    def trending_incident_type(self, prev):
        """
        Calculates the incident type for which the number of reports are currently increasing the most.
        """
        incident_type, increase = self.__largest_derivative(self.reported_incidents, prev.reported_incidents, IncidentType)
        if increase == 0:
            return 'The number of reported incidents is not increasing in any category.'
        else:
            return 'The number of reported incidents in the ' + incident_type.value + ' category are increasing the fastest.'

    def trending_region(self, prev):
        """
        Calculates the region in which the number of incident reports are currently increasing the most.
        """
        region, increase = self.__largest_derivative(self.affected_regions, prev.affected_regions, Region)
        if increase == 0:
            return 'The number of reported incidents is not increasing in any region.'
        else:
            return 'The number of reported incidents in the ' + region.value + ' region are increasing the fastest.'

    @staticmethod
    def __largest_derivative(dict1, dict2, keys):
        """
        Returns the key in keys which maximizes dict2[key] - dict1[key] and the value.
        """
        best_derivative = 0
        best_key = None
        for key in keys:
            if dict2[key] - dict1[key] > best_derivative:
                best_derivative = dict2[key] - dict1[key]
                best_key = key

        return best_key, best_derivative
