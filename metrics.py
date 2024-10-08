import requests
import sys
import signal
import re
import json
from os import getenv
from time import sleep
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import start_http_server

class TasmotaCollector(object):
    def __init__(self):
        # Read device config
        with open('/devices.json', 'r') as f:
            self.devices = json.load(f)

    def collect(self):
        for device in self.devices:
            try:
                response = self.fetch(device['ip'], device['user'], device['password'])
    
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
                    
                    r.add_metric([device['ip'], device['device_name']], metric)
                    yield r
            except:
                continue

    def fetch(self, ip, user, password):
        url = 'http://' + ip + '/?m=1'

        session = requests.Session()
        
        if user and password:
            session.auth = (user, password)

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
        sleep(1)
