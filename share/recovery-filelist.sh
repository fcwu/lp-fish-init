#!/bin/bash

bye() 
{
    mountpoint -q $TMPDIR && sudo umount $TMPDIR
    rmdir $TMPDIR
    exit 0
}
trap bye SIGHUP SIGINT SIGTERM

export TMPDIR=`mktemp -d /tmp/mount-recovery.XXXXXX`

mount_recovery()
{
    echo "mount \"$1\" \"$TMPDIR\""
    if ! sudo mount "$1" "$TMPDIR" && [ -f ${TMPDIR}/bto.xml ]; then
        return 1
    fi
    return 0
}

for mp in "/dev/sda2" "/dev/sda3"; do
    if mount_recovery $mp; then
        break
    fi
done

if ! mountpoint -q $TMPDIR; then
    echo "Failed to mount recovery partition"
fi

cd $TMPDIR
echo "Generate list..."
sudo find . -type f | xargs md5sum | sort -k 2 > /tmp/recovery-filelist.txt
cd - 2>&1 > /dev/null
sync
bye
exit 0
