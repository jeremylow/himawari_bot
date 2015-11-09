#!/bin/sh

cd $1
ffmpeg -framerate 6 -i "img%03d.png" -c:v libx264 -vf fps=6 -pix_fmt yuv420p $2
