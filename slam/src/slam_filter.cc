#include "slam_filter.h"
#include <math.h>
#include <random>
#include <numeric>

SlamParticle::SlamParticle(float weight, const vec3 &pos, const vec3 &ori)
    : weight_(weight), position_(pos), orientation_(ori) {}

void SlamParticle::AddLandmark(std::string id, const vec3 &relpos, const mat3 &conv) {
    landmark_filters_.insert({{id, SlamEKF(position_ + relpos, conv, id)}});
}

void SlamParticle::UpdateLandmark(std::string id, const vec3 &relpos) {
    landmark_filters_.at(id).Update(position_ + relpos);

    std::default_random_engine gen;
    std::exponential_distribution<float> exp(5);
    float a = exp(gen);
    if (a > .5) {
        a = .5;
    }
    position_ = (1-a)*position_ + a*(landmark_filters_.at(id).xhat_ - relpos);
}

float SlamParticle::UpdateWeight(std::string id, const vec3 &relpos, float certainty) {
    SlamEKF filter = landmark_filters_.at(id);
    vec3 error = position_ - (filter.xhat_ - relpos);
    Eigen::Matrix<float, 1, 1> normalized_error = certainty*error.transpose()*filter.covs_*error;
    weight_ = exp(-1 * normalized_error(0,0));
    return weight_;
}

void SlamParticle::UpdateParticle(const vec6 &u, float weight) {
    std::default_random_engine gen;
    // TODO: Tune
    std::uniform_real_distribution<float> uniform(.5, 1);
    std::normal_distribution<float> gaussian(0, 1);
    position_(0,0) += u(0,0)*dt*uniform(gen) + gaussian(gen)*dt*.03;
    position_(1,0) += u(1,0)*dt*uniform(gen) + gaussian(gen)*dt*.03;
    position_(2,0) += u(2,0)*dt*uniform(gen) + gaussian(gen)*dt*.03;

    orientation_(3,0) = u(3,0);
    orientation_(4,0) = u(4,0);
    orientation_(5,0) = u(5,0);

    weight_ = weight;
}

vec3 SlamParticle::GetState() {
    return position_;
}

vec3 SlamParticle::GetState(std::string id) {
    return landmark_filters_.at(id).xhat_;
}

SlamFilter::SlamFilter(int n): num_particles_(n) {
    for (int i = 0; i < n; ++i) {
        particles_.push_back(SlamParticle(1./n, vec3({0,0,0}), vec3({0,0,0})));
    }
}

SlamFilter::SlamFilter(int n, const vec3 &pos, const vec3 &ori): num_particles_(n) {
    for (int i = 0; i < n; ++i) {
        particles_.push_back(SlamParticle(1./n, pos, ori));
    }
}

void SlamFilter::NewLandmark(std::string id, const vec3 &relpos, const mat3 &cov) {
    for (SlamParticle particle: particles_) {
        particle.AddLandmark(id, relpos, cov);
    }
    landmarks_.insert(id);
}

void SlamFilter::NormalizeWeights() {
    float sum = std::accumulate(weights_.begin(), weights_.end(), 0);
    for (int i = 0; i < weights_.size(); ++i) {
        weights_[i] /= sum;
        particles_.at(i).weight_ = weights_[i];
    }
}

void SlamFilter::Update(const vec6 &u) {
    float total_weight = std::accumulate(weights_.begin(), weights_.end(), 0);
    float offset = total_weight/(weights_.size()*100);
    float total = total_weight + offset*weights_.size();
    for (int i = 0; i < weights_.size(); ++i) {
        weights_[i] = (weights_[i] + offset)/total;
        particles_.at(i).UpdateParticle(u, weights_[i]);
    }
}

void SlamFilter::UpdateLandmark(std::string id, const vec3 &relpos, float certainty) {
    for (int i = 0; i < particles_.size(); ++i) {
        particles_.at(i).UpdateLandmark(id, relpos);
        float w = particles_.at(i).UpdateWeight(id, relpos, certainty);
        weights_[i] = w;
    }
    NormalizeWeights();
    Resample();
}

void SlamFilter::Resample() {
    std::vector<SlamParticle> old_particles= particles_;
    std::vector<float> old_weights = weights_;

    std::default_random_engine gen;
    std::discrete_distribution<int> multi(weights_.begin(), weights_.end());

    for (int i = 0; i < particles_.size(); ++i) {
        int sampled = multi(gen);
        particles_[i] = old_particles[sampled];
        weights_[i] = old_weights[sampled];
    }
}
