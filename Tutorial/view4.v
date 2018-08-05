#!/bin/sh
rt -M \
 -o view4.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'rhc2.s' 'rpc.s' 'epa.s' 'ehy.s' \
 2>> view4.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845327e-01 2.73399687913068e-01 4.12746763261468e-01 7.50401850521824e-01;
eye_pt 3.52299264874985e+02 -2.13396157522892e+02 2.06944378323188e+02;
start 0; clean;
end;

EOF
