#!/bin/bash
WR="/var/www/IOTWeb"
PIDFILE="$WR/venv/.gunicorn_pid"
function error {
    echo "error occured with $1 - return value $2"
    return
}

function pull {
    echo pulling...
    sudo git -C $WR pull
    if [ "$?" != 0 ]; then
        error pull
    fi
}

function stop {
    echo stopping server...
    if [ -f $PIDFILE ]; then
        PID=$(cat $PIDFILE)
        sudo kill -s 0 $PID
        if [ "$?" == 0 ]; then
            sudo kill $PID
            if [ "$?" != 0 ]; then
                error stop
            fi
        fi
        rm -f $PIDFILE
        if [ "$?" != 0 ]; then
            error stop
        fi
    fi
}

function start {
    echo starting server...
    $WR/venv/bin/python $WR/venv/bin/gunicorn --chdir $WR IOTApp:app -p $PIDFILE -b 127.0.0.1:8000 -D
    if [ "$?" != 0 ]; then
        error start
    fi
}

function test {
    echo opening default server...
    cd $WR
    $WR/venv/bin/python $WR/IOTApp.py
}

if [ -z "$1" ]; then
    pull
    stop
    start
elif [ "$1" == "start" ]; then
    start
elif [ "$1" == "stop" ]; then
    stop
elif [ "$1" == "pull" ]; then
    pull
elif [ "$1" == "test" ]; then
    stop
    test
else
    echo "usage: . $WR/server.sh [command]"
    echo "commands available:"
    echo "    pull  - pulls the latest version of IOTWeb from"
    echo "            the server"
    echo "    stop  - stops the flask (gunicorn) server"
    echo "    start - starts the flask (gunicorn) server"
    echo "    text  - runs debugging with the internal server"
    echo "    help  - displays this message"
    echo "if command is omitted, it pulls and restarts the server"
fi
