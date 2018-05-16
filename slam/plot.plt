set xrange [-4:4]
set yrange [-4:4]
set key off
plot 'landmark.dat' using 1:2:3:4 with ellipses, \
     'particle.dat' using 1:2 with points pointtype 7
reread
