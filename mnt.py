#!/usr/bin/python

from ansible.module_utils.basic import *
import requests
import sys
import os


def main():
    module = AnsibleModule(
        argument_spec=dict(
            application=dict(required=True),
            businessUnit=dict(required=True),
            state=dict(required=True)
        ),
        supports_check_mode=True
    )
    params = module.params
    application = params['application']
    businessUnit = params['businessUnit']
    state = params['state']

    flag = [businessUnit]
    if application == "ABS_AZP_RAP":
      flag = ["{}-RAP".format(businessUnit)]
    elif application == "ABS_MAG_ADAPTER":
      flag = ["{}-ADAPTER".format(businessUnit)]
    elif application == "ABS_MAG_FSW" and businessUnit == "AGA-EU":
        flag = ["FSW_PRIMARY"]
    elif application == "ABS_MAG_FSW" and businessUnit == "AGA-GRP":
        flag = ["FSW_PRIMARY", "FSW_SECONDARY"]
    elif application == "GGI_TIP":
        flag = ["TIP"]
    elif application == "CISL_SEARCH_PROPERTIES":
        flag = ["CISL_SEARCH_BENEFICIARY"]

    if state == 'present':
       # create flag
       flagname = "/tmp/maintenance-deployment-running." + ''.join(flag)
       if not os.path.exists(flagname):
         open(flagname, "x")
       for i in flag:
         flagname = "/tmp/maintenance-svc." + i
         if not os.path.exists(flagname):
           open(flagname, "x")         
    elif state == 'absent':
       # remove flag
       flagname = "/tmp/maintenance-deployment-running." + ''.join(flag)
       if os.path.exists(flagname):
         os.remove(flagname)
       

    result = {"changed": 1, "rc": 0}
    module.exit_json(**result)


if __name__ == '__main__':
    main()
