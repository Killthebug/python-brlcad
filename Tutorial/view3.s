#!/bin/sh
rt -M \
 -o view3.s.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'rhc2.s' 'rpc.s' 'epa.s' \
 2>> view3.s.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845327e-01 2.73399687913068e-01 4.12746763261468e-01 7.50401850521824e-01;
eye_pt 2.02133528333830e+02 -1.29431318755312e+02 1.16100744795074e+02;
start 0; clean;
end;

EOF
