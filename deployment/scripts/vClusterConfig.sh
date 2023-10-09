#!/bin/bash

curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-linux-amd64" \
  && sudo install -c -m 0755 vcluster /usr/local/bin \
  && rm -f vcluster

vcluster connect $DEPLOY_ENVIRONMENT-vcluster -n $DEPLOY_ENVIRONMENT-vcluster &
