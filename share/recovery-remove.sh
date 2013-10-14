#!/bin/bash

bye() 
{
    sync
    if [ -n "$CURDIR" ]; then
        cd "$CURDIR"
    fi
    if [ -n "$MOUNTDIR" ]; then
        mountpoint -q $MOUNTDIR && sudo umount $MOUNTDIR
        rmdir $MOUNTDIR || :
    fi
    exit $1
}
trap bye SIGHUP SIGINT SIGTERM

export MOUNTDIR=`mktemp -d /tmp/mount-recovery.XXXXXX`
export CURDIR=`pwd`

mount_recovery()
{
    echo "mount \"$1\" \"$MOUNTDIR\""
    if ! sudo mount "$1" "$MOUNTDIR" || [ ! -f ${MOUNTDIR}/bto.xml ]; then
        return 1
    fi
    return 0
}

for mp in "/dev/sda2" "/dev/sda3"; do
    if mount_recovery $mp; then
        break
    fi
done

if ! mountpoint -q $MOUNTDIR; then
    echo "Failed to mount recovery partition"
    bye -1
fi

cd $MOUNTDIR
while read line
do
    echo "remove $line"
    sudo rm $line
done < "$1"
bye 0
