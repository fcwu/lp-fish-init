#!/bin/sh
# -*- coding: utf-8; indent-tabs-mode: nil; tab-width: 4; c-basic-offset: 4; -*-
#
# Copyright (C) 2013 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

HOST="http://162.213.34.36:5566"

print_help ()
{
    cat <<ENDLINE
$0 [-h|-i|-o|-s|-d|-p|-r|-t|-a|-j]
    -h This Help Manual
    -i import modaliases
    -o output modaliases
    -s specify a server
    -d download packages
    -p specify a project
    -r specify a repository
    -t specify tags
    -a use 'all' as tag combinator, 'any' by default
    -j use json as response format
ENDLINE
    exit 0
}

print_error ()
{
    echo "ERROR: $*"
    exit 1
}

import_modaliases ()
{
    [ -f "$1" ] || print_error "'$1' doesn't exist."
    cat "$1" >> ".modaliases.$$"
}

export_modaliases ()
{
    if [ -f ".modaliases.$$" ]; then
        cat ".modaliases.$$" | sort | uniq
        rm ".modaliases.$$"
    else
        find /sys -name modalias -exec cat {} \; 2>/dev/null | sort | uniq | while read modalias; do
            echo $modalias
        done
    fi
}

while getopts hi:o:s:dp:r:t:aj name; do
    case "$name" in
        (h)
            print_help
            ;;
        (i)
            import_modaliases $OPTARG
            ;;
        (o)
            export_modaliases >> $OPTARG
            exit
            ;;
        (s)
            HOST="$OPTARG"
            ;;
        (d)
            DOWNLOAD="yes"
            ;;
        (p)
            PROJECT='"project":"'"$OPTARG"'",'
            ;;
        (r)
            REPO='"repo":"'"$OPTARG"'",'
            ;;
        (t)
            TAGS='"tags":"'"$OPTARG"'",'
            ;;
        (a)
            COMBINATOR='"combinator":"'"all"'",'
            ;;
        (j)
            FORMAT='"format":"json",'
            ;;
    esac
done

if [ -f ".modaliases.$$" ]; then
    cat ".modaliases.$$" | sort | uniq > ".modaliases.$$.collect"
    rm ".modaliases.$$"
else
    export_modaliases > ".modaliases.$$.collect"
fi

MODALIASES="$(echo '"modaliases":['; cat .modaliases.$$.collect | sed 's/^/"/' | sed 's/$/",/'; echo -n ']')"
JSON="$(echo {$PROJECT$REPO$TAGS$COMBINATOR$FORMAT$MODALIASES} | sed 's/, ]}/]}/' | sed 's/\s\+//g')" # Remove trailing comma and white-space characters.
wget -q --header 'content-type: application/json' --post-data "$JSON" $HOST/api/v0/modalias/ -O - | sort | uniq | while read MODALIAS DEB; do
    if [ -n "$FORMAT" ]; then
        echo $MODALIAS $DEB
    else
        NAME="$(echo $DEB | cut -d '?' -f 1)"
        OPTION="$(echo $DEB | cut -d '?' -f 2 | sed 's/%3A/:/')"
        NAME="$(basename $NAME)"
        [ -n "$DOWNLOAD" ] || echo $MODALIAS $NAME $OPTION
        [ -n "$DOWNLOAD" ] && wget "$DEB" -O "$NAME"
    fi
done

rm ".modaliases.$$.collect"

# vim:fileencodings=utf-8:expandtab:tabstop=4:shiftwidth=4:softtabstop=4
