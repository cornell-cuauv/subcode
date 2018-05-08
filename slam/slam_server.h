#include <zmq.hpp>
#include "slam_filter.h"

class SlamServer {
    private:
        bool is_alive_;

        zmq::context_t ctx_;
        zmq::socket_t socket_;

        SlamFilter *filter_;

    public:
        SlamServer(SlamFilter *filter);

        void Listen();
        void Close();
};

