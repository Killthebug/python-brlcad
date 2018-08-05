#!/bin/sh
rt -M \
 -o test_wdb.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/test_wdb.g'\
 'hyperboloid.s' 'rcc.s' 'epa.s' 'rhc.s' 'tgc.s' 'rpc.s' 'trc.s' 'eto.s' 'bot.s' 'ehy.s' 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'sph1.s' 'box1.s' 'cone.s' 'arbn.s' 'pipe.s' 'grip.s' '_GLOBAL' 'text1.s' 'torus.s' 'wedge1.s' 'particle.s' 'submodel.s' 'ellipsoid.s' \
 2>> test_wdb.log\
 <<EOF
viewsize 2.20000000000000e+01;
orientation 5.90820389613820e-01 4.51608332919807e-01 4.74487291541428e-01 4.71002113604231e-01;
eye_pt 4.13342031440609e+01 -7.16029575513719e-01 -2.87503269899524e+00;
start 0; clean;
end;

EOF
