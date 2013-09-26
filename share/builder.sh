#!/bin/bash
CDIR=`pwd`
ROOT=`dirname $0`
trap_handler() 
{
    if [ -z $CDIR ]; then
        cd $CDIR
    fi
    exit 1
}
trap trap_handler SIGHUP SIGINT SIGTERM

cd ${ROOT}/installer
tar cjf ../payload.tbz ./*
cd ..

if [ -e "payload.tbz" ]; then
    if [ -e "payload.tbz" ]; then
        cat target-init.sh payload.tbz > ${CDIR}/fish-init-target
        rm payload.tbz
        chmod +x ${CDIR}/fish-init-target
    else
        echo "payload.tbz does not exist"
        exit 1
    fi
else
    echo "payload.tbz does not exist"
    exit 1
fi

echo "fish-init-target created"

exit 0
