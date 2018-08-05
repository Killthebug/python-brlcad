#!/bin/sh
rt -M \
 -o test2.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'rhc2.s' 'rpc.s' \
 2>> test2.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 6.18449525877659e-01 -6.18449525877659e-01 -3.42812170060660e-01 3.42812170060660e-01;
eye_pt -3.96018754208891e+01 -2.81376299080213e+01 -7.36774972690103e+01;
start 0; clean;
end;

EOF
