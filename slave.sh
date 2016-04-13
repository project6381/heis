#!/bin/sh

COMMAND="python slave.py"
LOGFILE=slave_log.txt

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}

writelog "Starting slave"
while true ; do
  $COMMAND
  writelog "Exited slave with status $?"
  writelog "Restarting slave"
done
