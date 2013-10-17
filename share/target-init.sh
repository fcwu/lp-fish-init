#!/bin/bash
echo "Installing..."

bye() 
{
    rm -rf $TMPDIR
    if [ -z $CDIR ]; then
        cd $CDIR
    fi
    rm -f /etc/sudoers.tmp
    rm -f /tmp/sudoers.new
    exit 0
}
trap bye SIGHUP SIGINT SIGTERM

export TMPDIR=`mktemp -d /tmp/selfextract.XXXXXX`
ARCHIVE=`awk '/^__ARCHIVE_BELOW__/ {print NR + 1; exit 0; }' $0`
tail -n+$ARCHIVE $0 | tar xjf - -C $TMPDIR

# ugly hack for recovery command
if basename "$0" | grep -q "01-fish-init-target"; then
    SUDO_USER=u
fi
if [ "$SUDO_USER" == "" ]; then
    echo "Usage: sudo $0"
    exit 1
elif [ "$SUDO_UID" == "0" ]; then
    echo "Do NOT run as root"
    exit 2
fi

CDIR=`pwd`
cd $TMPDIR
USER=$SUDO_USER


mkdir -p /home/${USER}/.ssh
cat <<EOF > /home/${USER}/.ssh/authorized_keys
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDL/zZW5wIsZGqEKmzWbiEYM3pm3rka5RZE3+5FjEDdzbsvlkZzwYRwIt5jXgoi/gYOiIOt58SdaegK4+E5ZD0jYXHIwB7uPZeVvaBvHFwI/TT0jAHn3rblWZRpDBCDp0Uq3DtHQfU9UrIwjOjPfUuE+cWdl/cnmLBoUWgtaFZpjeBcy4vf/zI69mDMucfJitdj/Ny9ZUVMibFFuCOCfZJCr3hgtb8Riv84SABVzAsX94pC1s/bRuItGg45Uj4e/fVIkJfiSZ1oLEjgxLyhkySH/upB3tPbxMxgj7p1Bc95DWwuvvYbspGjCxmaiDACXC78w9hNv6lOWbRq9PZ5nEtb u@u
EOF

if [ ! -f "/etc/sudoers.tmp" ]; then
    touch /etc/sudoers.tmp    
    cp /etc/sudoers /tmp/sudoers.new
    grep -q "^${USER}.*NOPASSWD" /tmp/sudoers.new || echo "${USER} ALL=NOPASSWD: ALL" >> /tmp/sudoers.new
    if visudo -c -f /tmp/sudoers.new; then
       cp /tmp/sudoers.new /etc/sudoers 
   else
       echo "E: create NOPASSWD sudo user"
   fi
    rm -f /etc/sudoers.tmp
    rm -f /tmp/sudoers.new
fi

dpkg -i ${TMPDIR}/*.deb || true

ips=`nmcli dev | grep ' connected' | awk '{print $1}' | xargs -I{} sh -c 'ifconfig {} | grep "inet addr" | sed -e "s/ *inet addr://" -e "s/ .*//"'`

if [ -z "$ips" ]; then
    echo "No avaiable network connection"
else
    if [ "$USER" == "u" ]; then
        uips=$ips
    else
        uips=`echo "$ips" | sed 's/^/$USER@/'`
    fi
    echo "Please connect this machine with address:" `echo $uips| sed 's/ /, /'`
fi

bye

exit 0

__ARCHIVE_BELOW__
