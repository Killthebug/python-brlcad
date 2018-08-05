#!/bin/sh
rt -M \
 -o view.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' \
 2>> view.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845328e-01 2.73399687913068e-01 4.12746763261469e-01 7.50401850521825e-01;
eye_pt 5.71802947664675e+01 -4.83810396362282e+01 2.84104448323595e+01;
start 0; clean;
end;

EOF
