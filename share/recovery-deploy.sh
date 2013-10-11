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
    if [ -n "$TMPDIR" ]; then
        rm -rf $TMPDIR
    fi
    exit $1
}
trap bye SIGHUP SIGINT SIGTERM

export MOUNTDIR=`mktemp -d /tmp/mount-recovery.XXXXXX`
export TMPDIR=`mktemp -d /tmp/deploy.XXXXXX`
export CURDIR=`pwd`

mount_recovery()
{
    echo "mount \"$1\" \"$MOUNTDIR\""
    if ! sudo mount "$1" "$MOUNTDIR" && [ -f ${MOUNTDIR}/bto.xml ]; then
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

echo "untar $1"
tar xvf "$1" -C "$TMPDIR"
cd $TMPDIR
for f in *; do
    if [[ "$f" =~ ^.*.tar.gz$ ]]; then
        sudo tar zvxf "$f" -C "$MOUNTDIR" --no-same-owner
        rm -f "$f"
    elif [[ "$f" =~ ^.*.deb$ ]]; then
        sudo mkdir -p "${MOUNTDIR}/debs"
        # NOT use mv to prevent from warning message
        #   mv: failed to preserve ownership
        sudo cp "$f" "${MOUNTDIR}/debs/"
        sudo rm "$f"
    else
        echo "Failed to handle $f"
        bye -1
    fi
done
bye 0
