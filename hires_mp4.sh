#!/bin/sh

cd $1
ffmpeg -framerate 6 -pattern_type glob -i '*.png' -c:v libx264 -vf fps=6 -pix_fmt yuv420p $2
