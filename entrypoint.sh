#!/bin/sh

# env >> /etc/environment
env | sed -r "s/'/\\\'/gm" | sed -r "s/^([^=]+=)(.*)\$/\1'\2'/gm"  >> /etc/environment

# execute CMD
echo "$@"
exec "$@"