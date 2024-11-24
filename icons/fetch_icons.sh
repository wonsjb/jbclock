#!/bin/sh

DIRECTORY=`dirname $0`
BASE_URI=https://openweathermap.org/img/wn

cd ${DIRECTORY}

for i in `cat codelist.txt`; do
    echo $i;
    wget ${BASE_URI}/${i}d@2x.png;
    wget ${BASE_URI}/${i}n@2x.png;
    wget ${BASE_URI}/${i}d.png;
    wget ${BASE_URI}/${i}n.png;
done
