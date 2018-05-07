#include <zmq.hpp>
#include <iostream>
#include <stdio.h>
#include <string.h>

#include "proto/slam_msg.pb.h"

//int main(int argc, char** argv) {
//    zmq::context_t ctx(1);
//    zmq::socket_t socket (ctx, ZMQ_REP);
//    socket.bind("tcp://127.0.0.1:57411");
//
//    while (true) {
//        zmq::message_t req;
//        socket.recv(&req);
//
//        slam::SlamMsg msg;
//        std::string msg_str(static_cast<char*>(req.data()), req.size());
//        msg.ParseFromString(msg_str);
//
//        zmq::message_t rep(8);
//        memcpy(rep.data(), "Recieved", 8);
//        socket.send(rep);
//
//        printf("%s: %f %f %f, %f %f %f\n", msg.id().c_str(), msg.m_x(), msg.m_y(), msg.m_z(), msg.u_x(), msg.u_y(), msg.u_z());
//    }
//    return 0;
//}
