#!/bin/sh
rt -M \
 -o view1.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'rhc2.s' \
 2>> view1.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845327e-01 2.73399687913068e-01 4.12746763261468e-01 7.50401850521824e-01;
eye_pt 8.87138273298980e+01 -6.60129448607538e+01 4.74868386992353e+01;
start 0; clean;
end;

EOF
#!/bin/sh
rt -M \
 -o view1.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' 'rhc2.s' 'rpc.s' \
 2>> view1.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.37938103845327e-01 2.73399687913068e-01 4.12746763261468e-01 7.50401850521824e-01;
eye_pt 1.26965507908475e+02 -8.74012874910913e+01 7.06274151844196e+01;
start 0; clean;
end;

EOF
