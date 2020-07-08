from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import smtplib
import json
from datetime import datetime
from ansible.module_utils._text import to_bytes
from ansible.plugins.callback import CallbackBase


def v2_playbook_on_play_start(self, play):
    var_mgr = play.get_variable_manager()
    self.play = play
    self.extra_vars = var_mgr.extra_vars
    self.results.append(self._new_play(play))

def v2_playbook_on_stats(self, stats):
    sendmail(self, stats)

def v2_playbook_on_task_start(self, task, is_conditional):
    self.results[-1]['tasks'].append(self._new_task(task))

def v2_runner_on_ok(self, result, **kwargs):
    host = result._host
    self.results[-1]['tasks'][-1]['hosts'][host.name] = result._result
