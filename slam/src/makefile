CC=g++
CFLAGS=-std=c++11 -lzmq -lprotobuf -I /usr/include/eigen3
DEPS = ekf.h slam.h slam_server.h util.h
OBJ = ekf.o slam.o slam_server.o main.o

%.o: %.cc $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

slam: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS)

clean:
	rm -f *.o slam
