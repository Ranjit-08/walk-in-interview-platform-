#!/bin/bash
# Minimal bootstrap — GitHub Actions handles everything else
apt-get update -y
apt-get install -y openssh-server curl
systemctl enable ssh
echo "EC2 ready" > /var/log/ec2-ready.log