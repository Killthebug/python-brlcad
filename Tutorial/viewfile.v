#!/bin/sh
rt -M \
 -o view9.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'hyperboloid.s' 'rcc.s' 'rec.s' 'tec.s' 'epa.s' 'tgc.s' 'rpc.s' 'trc.s' 'eto.s' 'ehy.s' 'rhc2.s' 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'sph1.s' 'cone.s' 'arbn.s' 'pipe.s' '_GLOBAL' 'torus.s' 'particle.s' 'ellipsoid.s' 'ellipsoid2.s' \
 2>> view9.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845327e-01 2.73399687913068e-01 4.12746763261468e-01 7.50401850521824e-01;
eye_pt 2.53515779019619e+03 -1.43393665803367e+03 1.52747730097117e+03;
start 0; clean;
end;

EOF
