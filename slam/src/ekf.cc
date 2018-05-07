#include "ekf.h"

SlamEKF::SlamEKF(const Eigen::Matrix<float, 3, 1> &x, 
                 const Eigen::Matrix<float, 3, 3> &p,
                 std::string id):
    B_(mat3::Zero()), R_(mat3::Zero()), Q_(mat3::Zero()), xhat_(x), covs_(p), id_(id) {}

void SlamEKF::Predict(const Eigen::Matrix<float, 3, 1> &u) {
    xhat_ = xhat_ + B_*u;
    covs_ = covs_ + Q_;
}

void SlamEKF::Update(const Eigen::Matrix<float, 3, 1> &z) {
    Eigen::Matrix<float, 3, 3> H = mat3::Identity();
    Eigen::Matrix<float, 3, 1> y = z - xhat_;
    Eigen::Matrix<float, 3, 3> S = H*covs_*H.transpose() + R_;
    Eigen::Matrix<float, 3, 3> K = covs_*H.transpose()*S.inverse();
    xhat_ = xhat_ + K*y;
    covs_ = (Eigen::Matrix<float, 3, 3>::Identity() - K*H)*covs_;
}
