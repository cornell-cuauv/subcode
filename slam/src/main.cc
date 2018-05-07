#include "slam.h"
#include "slam_server.h"
#include <unistd.h>
#include <stdio.h>

int main(int argc, char** argv) {
    SlamEKF e(vec3::Zero(), mat3::Identity(), "test");

    while (true) {
        printf("%f\n", e.xhat_[0]);
        e.Predict(vec3::Zero());
        e.Update(vec3({1,2,3}));
        sleep(1);
    }

    return 0;
}
