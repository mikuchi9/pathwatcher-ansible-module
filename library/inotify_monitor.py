#!/usr/bin/python

# Copyright: (c) 2025, mikuchi9 <dustycrocodile9@gmail.com>
# Based on the Ansible module skeleton from the official documentation:
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html#creating-a-module
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import

DOCUMENTATION = r'''
module: inotify_monitor

short_description: Watches for filesystem events on paths

version_added: "1.0.0"

description:
  This module is based on the `inotify_simple` Python package: https://inotify-simple.readthedocs.io/en/latest/,
  which is a simple Python wrapper around `inotify(7)`. Multiple paths can be watched at the same time, with 
  each path having a separate watcher thread. A time limit must be specified when running this module.
  The result is saved in a variable (please specify a reasonable time limit, as a too-large value can lead 
  to unpredictable results), which will be printed in the output when the module exits or saved to a file 
  in `.csv` format.
  This module is written with the assumption that it will be used to watch events for a short time frame, 
  not for long durations like 6 or 7 hours. The effectiveness of the monitoring also depends on how heavily 
  changes might occur on the monitored paths.

options:
    watch_paths:
        description: Path(s) to monitor. Multiple paths should be comma-separated, e.g., /path/to/dir1,/path/to/dir2
        required: true
        type: str
    stimeout:
    mtimeout:
        description:
            - Sets the time limit while the path(s) is/are monitored.
            - `stimeout` specifies the time limit in seconds, while `mtimelimit` specifies the time limit in minutes.
        required: One of these is necessary, but not both at the same time.
        type: int

author:
    - mikuchi9 (@mikuchi9)
'''

EXAMPLES = r'''
# Watch a single directory for changes for 30 seconds
- name: Monitor directory
  hosts: remotehost
  tasks:
    - name: Use inotify_monitor module
      inotify_monitor:
        watch_paths: /tmp
        stimeout: 30
      register: logs
    - name: Dump the logs
      debug:
        msg: '{{ logs }}'

# Watch two paths for changes for 5 minutes and write logs to a file
- name: Monitor paths
  hosts: localhost
  tasks:
    - name: Use inotify_monitor module
      inotify_monitor:
        watch_paths: /tmp,/etc/host.conf
        mtimeout: 5
        log_file: ~/inotify_logs
      register: logs
    - name: Dump the logs
      debug:
        msg: '{{ logs }}'
'''

RETURN = r'''
*sample: '"path,name,event(s)\n",
         "/tmp,myfile,['CREATE']\n",
         "/tmp,myfile,['OPEN']\n",
         "/tmp,myfile,['ATTRIB']\n",
         "/tmp,myfile,['CLOSE_WRITE']\n"'

*sample: 'logs are written to the '~/inotify_logs''
'''

from ansible.module_utils.basic import AnsibleModule

import threading
import queue
import time
import os

from inotify_simple import INotify, masks, flags

logs = ["path,name,event(s)\n"]

def watcher_switch(watcher, watcher_queue, path, switch = 'start'):
    """Starting or stopping watchers based on the switch value ("start" or "stop"), 
       passing them through queues and storing inotify events in the `logs` variable."""
    while True:
        if watcher_queue.qsize() > 0:    
            switch = watcher_queue.get(block=False)
        if switch == 'start':
            for event in watcher.read(timeout=0.1):
                eflags = [f.name for f in flags.from_mask(event.mask)]
                log_line = path + ","
                log_line = log_line + str(event.name) + ","
                log_line = log_line + str(eflags) + '\n'
                logs.append(log_line)
        if switch == 'stop':
            watcher.close()
            break
        time.sleep(0.1)

def stop_watchers(queues):
    """stopping watchers by sending 'stop' via queues"""
    
    for i, _ in enumerate(queues):
        queues[i].put('stop')

def run_module():
    
    module_args = dict(
        watch_paths=dict(type='str', required=True),
        stimeout=dict(type='int', required=False),
        mtimeout=dict(type='int', required=False),
        log_file=dict(type='str', required=False),
    )
    
    mutually_exclusive = [
        ['stimeout', 'mtimeout']
    ]
    
    module = AnsibleModule(
        argument_spec=module_args,
        mutually_exclusive=mutually_exclusive,
    )


    stimeout = module.params.get('stimeout')
    mtimeout = module.params.get('mtimeout')

    log_file = module.params.get('log_file')
    
    paths = module.params['watch_paths'].split(',')
    watchers = {}
    for i, p in enumerate(paths):
        watchers[i] = INotify()
        watchers[i].add_watch(p, masks.ALL_EVENTS)
        
    threads = {}
    queues = {}
    for i, _ in enumerate(watchers):
        watcher_queue = queue.Queue()    
        queues[i] = watcher_queue
        threads[i] = threading.Thread(name='custom_filesystem_watcher__Child_process__' + str(i), 
                                      target=watcher_switch, 
                                      args=(watchers[i], watcher_queue, paths[i], ))

        queues[i].put('start')
        threads[i].start()

    started = time.time()

    if mtimeout:
        timeout = mtimeout * 60
    else:
        timeout = stimeout

    while (time.time() - started) < timeout:
        time.sleep(0.1)

    stop_watchers(queues)

    if log_file:
        log_file = os.path.expanduser(log_file)
        log_file_msg = "logs are written to the '" + log_file + "'"
        with open(log_file, 'w') as file:
            file.writelines(logs)
        file.close()
        module.exit_json(log_msg=log_file_msg)
    
    module.exit_json(log=logs)


def main():
    run_module()


if __name__ == '__main__':
    main()
