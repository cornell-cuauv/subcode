#include "slam_server.h"
#include "ekf.h"
#include <unistd.h>
#include <iostream>

int main(int argc, char** argv) {
    SlamEKF e(vec3::Zero(), mat3::Identity(), "test");

    vec3 goal({1,2,3});
    for (int i = 1; i > 0; ++i) {
        if (i % 10 == 0) {
            goal += vec3({.2,-.2,0});
        }
        std::cout << e.xhat_ << std::endl;
        std::cout << "--" << std::endl;
        std::cout << e.covs_ << std::endl << std::endl;

        e.Predict(vec3::Zero());
        e.Update(goal);
        sleep(1);
    }

    return 0;
}
