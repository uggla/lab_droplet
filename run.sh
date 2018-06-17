#!/bin/sh

docker run --rm -d -p 80:5000 -v $PWD/data:/usr/src/app/data --name lab_droplet  --env-file credentials.env -ti lab_droplet
