import requests
import sys
import signal
import re
from os import getenv
from time import sleep
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import start_http_server


class TasmotaCollector(object):
    def __init__(self):
        self.ip = getenv('DEVICE_IP')
        if not self.ip:
            self.ip = "192.168.4.1"
        self.user = getenv('USER')
        self.password = getenv('PASSWORD')
        self.device_name = getenv('DEVICE_NAME')

    def collect(self):

        response = self.fetch()

        for key in response:
            safe_key = re.sub(r'[^A-Za-z0-9_]+', '', key).lower().replace(" ", "_") 
            
            metric_name = "tasmota_" + safe_key
            metric = response[key].split()[0]

            unit = None
            if len(response[key].split()) > 1:
                unit = re.sub(r'[^A-Za-z0-9_]+', '', response[key].split()[1])

            if "today" in metric_name or "yesterday" in metric_name or "total" in metric_name:
                r = CounterMetricFamily(metric_name, safe_key, labels=['device', 'device_name'], unit=unit)
            else:
                r = GaugeMetricFamily(metric_name, safe_key, labels=['device', 'device_name'], unit=unit)
            
            r.add_metric([self.ip, self.device_name], metric)
            yield r

    def fetch(self):

        url = 'http://' + self.ip + '/?m=1'

        session = requests.Session()
        
        if self.user and self.password:
            session.auth = (self.user, self.password)

        page = session.get(url)

        values = {}


        string_values = str(page.text).split("{s}")
        for i in range(1,len(string_values)):
            try:
                label = string_values[i].split("{m}")[0]
                value = string_values[i].split("{m}")[1].split("{e}")[0]
                if "<td" in value:
                    value = value.replace("</td><td style='text-align:left'>", "")
                    value = value.replace("</td><td>&nbsp;</td><td>", "")

                values[label] = value
            except IndexError:
                continue
        return values

def signal_handler(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':

    port = getenv('EXPORTER_PORT')
    if not port:
        port = 8000

    start_http_server(int(port))
    REGISTRY.register(TasmotaCollector())

    while(True):
        sleep(5)
    
