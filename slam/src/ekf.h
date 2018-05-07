#ifndef SLAM_EKF_H
#define SLAM_EKF_H

#include "util.h"
#include <string>

class SlamEKF {
    public:
        Eigen::Matrix<float, 3, 1> xhat_;
        Eigen::Matrix<float, 3, 3> covs_;
        std::string id_;
    protected:
        Eigen::Matrix<float, 3, 3> B_;
        Eigen::Matrix<float, 3, 3> R_;
        Eigen::Matrix<float, 3, 3> Q_;

    public:
        SlamEKF(const Eigen::Matrix<float, 3, 1> &x, 
                const Eigen::Matrix<float, 3, 3> &p,
                std::string id);

        void Predict(const Eigen::Matrix<float, 3, 1> &u);
        void Update(const Eigen::Matrix<float, 3, 1> &z);
};

#endif
