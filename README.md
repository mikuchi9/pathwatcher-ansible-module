## Description
This module monitors inotify events on specified paths.

## Preperation
You must install the `inotify_simple` Python package.
See the example `install_necessary_pkgs.yml`.

## Run
Adhoc Example 1. Run the module to monitor `/tmp` and `/etc/host.conf` paths for 4 minutes on localhost
`ANSIBLE_LIBRARY=./library ansible -m inotify_monitor -a 'watch_paths=/tmp,/etc/host.conf mtimeout=4' localhost`

Adhoc Example 2. Run the module to monitor `/tmp` directory for 80 seconds on remote host
`ANSIBLE_LIBRARY=./library ansible -m inotify_monitor -a 'watch_paths=/tmp stimeout=80' _remotehost_`


* After installing the `inotify_simple` module, if it cannot be found, try deactivating and then reactivating the environment if you installed it inside virtual environment.