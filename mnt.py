#!/usr/bin/python

from ansible.module_utils.basic import *
import requests
import sys


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

    if state == 'present':
       # create flag
    elif state == 'absent':
       # remove flag

    result = {"changed": 1, "rc": 0}
    module.exit_json(**result)


if __name__ == '__main__':
    main()
