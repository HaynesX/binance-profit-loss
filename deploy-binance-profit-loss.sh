#!/bin/bash

set -e

DOCKER_IMAGE_TAG=$1


cd binance-profit-loss

echo "Shutting Down Previous Containers."

sudo docker-compose -f docker-compose-binance-profit-loss.yaml down

cd ..

echo "Deleting previous directory"

rm -rf binance-profit-loss

echo "Cloning Repo"

git clone https://github.com/HaynesX/binance-profit-loss.git

cd binance-profit-loss

echo "Checkout new version"

git checkout tags/$DOCKER_IMAGE_TAG

echo "Starting Docker Container for Image $DOCKER_IMAGE_TAG"

sudo TAG=$DOCKER_IMAGE_TAG docker-compose -f docker-compose-binance-profit-loss.yaml up -d


