#include "slam_server.h"
#include "slam_filter.h"
#include <iostream>

int main(int argc, char** argv) {
    SlamFilter e = SlamFilter(2);

    vec6 goal = vec6::Zero();
    std::string x;
    for (int i = 1; i > 0; ++i) {
        std::cin >> x; 
        if (x == "u") {
            int u;
            std::cin >> u;
            goal(0, 0) = u;
            std::cout << goal.transpose() << std::endl;
            e.Update(goal);
        }
        else if (x == "l") {
            float a, b, c;
            std::cin >> x;
            std::cin >> a;
            std::cin >> b;
            std::cin >> c;
            e.Landmark(x, vec3({a,b,c}), mat3::Identity()*.01);
        }
        else {
            std::cout << "Try again?" << std::endl;
        }
        std::cout << e << std::endl;
    }

    return 0;
}
