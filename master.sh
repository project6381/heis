#!/bin/sh

COMMAND="python master.py"
LOGFILE=master_log.txt

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}

writelog "Starting master"
while true ; do
  $COMMAND
  writelog "Exited master with status $?"
  writelog "Restarting master"
done
