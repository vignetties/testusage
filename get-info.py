from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import requests
import subprocess
import datetime
import time
import json
import urllib3
from ansible.module_utils._text import to_bytes
from ansible.plugins.callback import CallbackBase

def deployment_info(self, stats):
    app = self.extra_vars.get("APP", None)
    version = self.extra_vars.get("VERSION", None)
    tenant = self.extra_vars.get("TENANT", None)
    jobid = self.extra_vars.get("tower_job_id", None)
    launchtype = self.extra_vars.get("tower_job_launch_type", None)
    templatename = self.extra_vars.get("tower_job_template_name", None)
    ppmurl = self.extra_vars.get("PPMURL", None)
    stage = self.extra_vars.get("STAGE", None)
    username = self.extra_vars.get("tower_user_name", None)
    requestid = self.extra_vars.get("REQUESTID", None)
    deployment_info = self.extra_vars.get("DEPLINFO", None)
    ansible_hostname = self.extra_vars.get("ansible_hostname", None)
    now = datetime.datetime.now()
    epoch = time.time()
    epoch = int(epoch)
    hosts = sorted(stats.processed.keys())
    hostsInScope = []
    
    statusname = "Successful"
    for h in hosts:
        hostsInScope.append(h)
        s = stats.summarize(h)
        errors = sum([s['failures'], s['unreachable']])
        if errors > 0:
            statusname = "Failed"

    #only send post request when status is success
    if statusname == "Successful":
        nonprod = ['DEV', 'TEST', 'TEXT', 'PREPROD', 'MNTN', 'QA', 'EDU', 'JIT']
        if stage == 'PROD':
            base_url = "https://awp-elk-prod.srv.allianz/grafana/api/annotations/graphite"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer eyJrIjoiN1habmF3Z3dZYXVzNjZBU0RDcUxnRDZHMnBWU3QwWFYiLCJuIjoiYWRtaW4iLCJpZCI6MX0='
            }
        elif stage in nonprod:
            base_url = "https://awp-elk-nonprod.srv.allianz/grafana/api/annotations/graphite"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer eyJrIjoiZ0cyY3JYbDVCNWlJcmwyWG5LWUlvTUJSYzRITDhmaVciLCJuIjoiQWRtaW4iLCJpZCI6MX0='
            }
        else:
            print("Wrong STAGE defined")
    
        if app.startswith('ABS_')  or app.startswith('CISL_MEDIATOR') or app.startswith('CISL_SEARCH') or app.startswith('DISPATCH_SCHEDULER'):
            if app.startswith('ABS_') and app != "ABS_MAG":
                platform = "ABS "
                component = app.split("_", 2)
                component = component[2]
            elif (app == 'CISL_MEDIATOR') or app.startswith('CISL_SEARCH') or (app == 'DISPATCH_SCHEDULER'):
                platform = "ASIF "
                component = app
            elif app == "ABS_MAG":
                platform = "ABS "
                component = app
        
            what = platform + stage + " Deployment"
            data = platform + "V" + version
            tags = platform + component + " " + stage

            if "-" in tenant:
                ten = tenant.split("-",2)
                ten = ten[1]
            else:
                ten = tenant.split(" ",2)
                if ten[1] == "Europe":
                    ten = "EU"
                elif ten[1] == "EU":
                    ten = "EU"

            payload = {
            'what': what,
            'tags': [platform,component,stage],
            'when': epoch,
            'data': data
            }
            payload = json.dumps((payload))
            cafile='/etc/ssl/certs/ca-bundle.crt'
            certs = requests.certs.where()

            if (ten == "EU") or (ten == "Europe"):
                #print("Data: %s %s %s" % (base_url, payload, headers))
                response = requests.post(base_url, data=payload, verify=False, headers=headers)    

                count = 1

                if response.status_code == 200:
                    print("Data successfully sent to Grafana.")
                else:
                    while count <= 5:
                        #print("ReturnCode: %s" % response.status_code)
                        print("Request %i" % count)
                        response = requests.post(base_url, data=payload, verify=False, headers=headers)
                        if response.status_code == 200:
                            print("Data successfully sent to Grafana.")
                            break
                        else:
                            count = count + 1
                    if count > 5:
                        print("Sending data to Grafana failed 5 times - sent mail to azp-devops.")
                        cmd = ("mail -s \"Deployment info failed\" -r root@LX-ANSIBLE01 azp-devops@allianz.at <<< \"https://ansible.aeat.allianz.at/#/jobs/playbook/%s \nStatus code: %s\"" % (jobid, response.status_code))
                        subprocess.call([cmd], shell=True)

    urllib3.PoolManager(
        cert_reqs = 'CERT_REQUIRED',
        ca_certs = '/etc/pki/tls/certs/ca-bundle.crt'
    )

class CallbackModule(CallbackBase):

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)
        self.results = []
        self.play = None
        self.extra_vars = None
        self.failure = False

    def _new_play(self, play):
        return {
            'play': {
                'name': play.name,
                'id': str(play._uuid)
            },
            'tasks': []
        }

    def _new_task(self, task):
        return {
            'task': {
                'name': task.name,
                'id': str(task._uuid)
            },
            'hosts': {}
        }

    def v2_playbook_on_play_start(self, play):
        var_mgr = play.get_variable_manager()
        self.play = play
        self.extra_vars = var_mgr.extra_vars
        self.results.append(self._new_play(play))

    def v2_playbook_on_stats(self, stats):
        deployment_info(self, stats)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))
    
    def v2_runner_on_ok(self, result, **kwargs):
        deployment_info(self, result)
        host = result._host
        self.results[-1]['tasks'][-1]['hosts'][host.name] = result._result
        notify(self.results);
