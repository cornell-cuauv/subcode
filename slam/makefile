CC=g++
CFLAGS=-std=c++11 -lzmq -lprotobuf -I /usr/include/eigen3
DEPS = ekf.h slam_filter.h slam_server.h util.h proto/slam_msg.pb.h
OBJ = ekf.o slam.o slam_server.o slam_filter.o proto/slam_msg.pb.o

%.o: %.cc $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

slam: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS)

clean:
	rm -f *.o slam
