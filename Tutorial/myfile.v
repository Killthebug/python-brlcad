#!/bin/sh
rt -M \
 -o myfile.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' \
 2>> myfile.v.log\
 <<EOF
viewsize 1.18778504000000e+02;
orientation 4.12926216610839e-01 2.94213915968230e-01 3.95567729778661e-01 7.65804336918940e-01;
eye_pt 3.93105094266372e+01 -4.18300258103769e+01 3.45939007987432e+01;
start 0; clean;
end;

EOF
#!/bin/sh
rt -M \
 -o myfile.v.pix\
 $*\
 '/Users/Troller/Documents/GSoC/brlcad/python-brlcad/Tutorial/scene.g'\
 'arb4.s' 'arb5.s' 'arb6.s' 'arb7.s' 'arb8.s' \
 2>> myfile.v.log\
 <<EOF
viewsize 9.66098120000000e+01;
orientation 4.53696891593095e-01 3.35635079015433e-01 3.65097289257176e-01 7.40413528827056e-01;
eye_pt 5.02208123973488e+01 -4.38801833337795e+01 1.83593223558206e+01;
start 0; clean;
end;

EOF
