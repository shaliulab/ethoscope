#! /bin/bash

PROGNAME=$0

usage() {
  cat << EOF >&2
Usage: $PROGNAME [-h <host> ] [-p <port> ]

-h <host>: URL to host running ethoscope_node service
-p <port>: Port in the remote server where the ethoscope_node is running
EOF
  exit 1
}

HOST=cv1 PORT=80
while getopts dn:t o; do
  case $o in
    (h) HOST=$OPTARG;;
    (p) PORT=$OPTARG;;
    (*) usage
  esac
done
shift "$((OPTIND - 1))"

#echo Remaining arguments: "$@"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
PLAIN='\033[0m'

next() {
    printf "%-70s\n" "-" | sed 's/\s/-/g'
}

#kill_mirror() {
#  PORT=$1
#  echo $PORT
#  PID=$((lsof -i :$PORT | tail -n +2 | awk '{print $2}'))
#  echo $PID
#  #kill $PID
#  #printf "${RED}Killing existing mirror on port $PORT\n${PLAIN}"
#  exit 1
#}
next
printf "${BLUE}Mirroring GUI running on $HOST:$PORT\n${PLAIN}"
#ssh -fL 80:127.0.0.1:$PORT $HOST || kill_mirror $PORT
ssh -fNL 80:127.0.0.1:$PORT $HOST 
printf "${GREEN}Mirroring done\n${PLAIN}"
