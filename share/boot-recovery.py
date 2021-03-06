#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
from tempfile import NamedTemporaryFile


AUTO_INSTALL = '''
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

if ! grep -q "FISH-INIT-HACK >>>" ${MOUNTDIR}/preseed/dell-recovery.seed; then
    cat <<EOF >> ${MOUNTDIR}/preseed/dell-recovery.seed
### FISH-INIT-HACK >>>
ubiquity oem-config/enable boolean false

### Timezone ###
ubiquity time/zone select Asia/Taipei

### User configuration ###
ubiquity passwd/user-fullname string u-fish-init
ubiquity passwd/username string u
ubiquity passwd/user-password password u
ubiquity passwd/user-password-again password u
ubiquity passwd/auto-login boolean true
ubiquity user-setup/allow-password-weak boolean true
### FISH-INIT-HACK <<<
EOF
fi

mkdir -p ${MOUNTDIR}/scripts/chroot-scripts/os-post/
cat <<EOF > ${MOUNTDIR}/scripts/chroot-scripts/os-post/00-build-dell-recovery-part
#!/usr/bin/python
import Dell.recovery_common as magic
import os
import subprocess

rpart = magic.find_factory_rp_stats()
if rpart:
    rec_text = "Restore Ubuntu " + os.popen('lsb_release -r -s').readline().strip() + " to factory state"
    magic.process_conf_file(original = '/usr/share/dell/grub/99_dell_recovery', \
                            new = '/etc/grub.d/99_dell_recovery',               \
                            uuid = str(rpart["uuid"]),                          \
                            rp_number = str(rpart["number"]),                   \
                            recovery_text = rec_text)

    os.chmod('/etc/grub.d/99_dell_recovery', 0755)
    subprocess.call(['update-grub'])
EOF
mkdir -p ${MOUNTDIR}/scripts/chroot-scripts/os-post/
cp -v /tmp/fish-init-target ${MOUNTDIR}/scripts/chroot-scripts/os-post/01-fish-init-target
bye 0
'''


class RestoreFailed(Exception):
    def __init__(self, msg):
        self.msg = msg


def prepare_reboot():
    """Helper function to reboot into an entry"""
    #find our one time boot entry
    dest = "99_dell_recovery"
    if not os.path.exists("/etc/grub.d/%s" % dest):
        raise RestoreFailed("missing %s to parse" % dest)

    with open('/etc/grub.d/%s' % dest) as rfd:
        grub_file = rfd.readlines()

    entry = False
    for line in grub_file:
        if "menuentry" in line:
            split = line.split('"')
            if len(split) > 1:
                entry = split[1]
                break

    if not entry:
        raise RestoreFailed("Error parsing %s for bootentry." % dest)

    #set us up to boot saved entries
    with open('/etc/default/grub', 'r') as rfd:
        default_grub = rfd.readlines()
    with open('/etc/default/grub', 'w') as wfd:
        for line in default_grub:
            if line.startswith("GRUB_DEFAULT="):
                line = "GRUB_DEFAULT=saved\n"
            wfd.write(line)

    #Make sure the language is set properly
    with open('/etc/default/locale', 'r') as rfd:
        for line in rfd.readlines():
            if line.startswith('LANG=') and len(line.split('=')) > 1:
                lang = line.split('=')[1].strip('\n').strip('"')
    env = os.environ
    env['LANG'] = lang

    ret = subprocess.call(['/usr/sbin/update-grub'], env=env)
    if ret is not 0:
        raise RestoreFailed("error updating grub configuration")

    ret = subprocess.call(['/usr/sbin/grub-reboot', entry])
    if ret is not 0:
        raise RestoreFailed("error setting one time grub entry")

    if '-a' in sys.argv:
        with NamedTemporaryFile(delete=False) as f:
            f.write(AUTO_INSTALL)
            f.close()
            if subprocess.call(['/bin/sh', f.name]) is not 0:
                logging.critical('Failed to run automatic install script')
            os.unlink(f.name)


def main():
    try:
        if os.getuid() != 0:
            print >> sys.stderr, "sudo as root... (UID={})".format(os.getuid())
            sys.exit(subprocess.call(['/usr/bin/sudo'] + sys.argv))
        prepare_reboot()
        subprocess.Popen(['/usr/bin/sudo',
                          '/bin/sh', '-c',
                          'sleep 5; /sbin/reboot'])
        print "rebooting..."
        sys.exit(0)
    except RestoreFailed as e:
        print >> sys.stderr, e.msg
    sys.exit(-1)


if __name__ == '__main__':
    main()
