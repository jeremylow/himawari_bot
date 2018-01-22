#!/bin/sh

cd $1

# MP4-specific customization
ffmpeg -framerate 8 -pattern_type glob -i "*.JPG" -s 1000:1000 -sws_flags lanczos -sws_dither none -vf unsharp=5:5:0:5:5:0 $2
