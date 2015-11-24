#!/bin/sh

palette="/tmp/palette.png"

filters="fps=6"

ffmpeg -framerate 6 -pattern_type glob -i "lowres/*.png" -vf "$filters,palettegen" -y $palette
ffmpeg -framerate 6 -pattern_type glob -i "lowres/*.png" -i $palette -lavfi "$filters [x]; [x][1:v] paletteuse" -y $1
