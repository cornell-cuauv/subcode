#include "slam_filter.h"
#include <math.h>
#include <chrono>
#include <numeric>

SlamParticle::SlamParticle(float weight, const vec3 &pos, const vec3 &ori)
    : weight_(weight), position_(pos), orientation_(ori) {

        unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
        gen_ = std::default_random_engine(seed);
        uniform_ = std::normal_distribution<float>(.9, .1);
        gaussian_ = std::normal_distribution<float>(0, 1);
}


void SlamParticle::AddLandmark(std::string id, const vec3 &relpos, const mat3 &conv) {
    landmark_filters_.insert({{id, SlamEKF(position_ + relpos, conv, id)}});

}

void SlamParticle::UpdateLandmark(std::string id, const vec3 &relpos) {
    landmark_filters_.at(id).Update(position_ + relpos);

    std::exponential_distribution<float> exp(5);
    float a = exp(gen_);
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
    position_(0,0) += u(0,0)*dt*uniform_(gen_) + gaussian_(gen_)*dt*.03;
    position_(1,0) += u(1,0)*dt*uniform_(gen_) + gaussian_(gen_)*dt*.03;
    position_(2,0) += u(2,0)*dt*uniform_(gen_) + gaussian_(gen_)*dt*.03;

    orientation_(0,0) = u(3,0);
    orientation_(1,0) = u(4,0);
    orientation_(2,0) = u(5,0);

    weight_ = weight;
}

void SlamParticle::ReinitRandom() {
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    gen_ = std::default_random_engine(seed);
}

vec3 SlamParticle::GetState() {
    return position_;
}

vec3 SlamParticle::GetState(std::string id) {
    return landmark_filters_.at(id).xhat_;
}

std::ostream& operator<<(std::ostream &os, const SlamParticle &sp) {
    os << "Particle Weight: " << sp.weight_ << std::endl;
    os << "Particle Pos: " << sp.position_.transpose() << std::endl;
    for (auto elem: sp.landmark_filters_) {
        os << "Landmark: " << elem.first << "\t" << elem.second.xhat_.transpose() << std:: endl;
    }
    return os;
}

SlamFilter::SlamFilter(int n): num_particles_(n) {
    for (int i = 0; i < n; ++i) {
        particles_.push_back(SlamParticle(1./n, vec3({0,0,0}), vec3({0,0,0})));
        weights_.push_back(1./n);
    }
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    gen_ = std::default_random_engine(seed);
}

SlamFilter::SlamFilter(int n, const vec3 &pos, const vec3 &ori): num_particles_(n) {
    for (int i = 0; i < n; ++i) {
        particles_.push_back(SlamParticle(1./n, pos, ori));
        weights_.push_back(1./n);
    }
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    gen_ = std::default_random_engine(seed);
}

void SlamFilter::Update(const vec6 &u) {
    float total_weight = std::accumulate(weights_.begin(), weights_.end(), 0.);
    std::cout << total_weight << std::endl;
    float offset = total_weight/(weights_.size()*100);
    float total = total_weight + offset*weights_.size();
    for (int i = 0; i < weights_.size(); ++i) {
        weights_[i] = (weights_[i] + offset)/total;
        particles_.at(i).UpdateParticle(u, weights_[i]);
    }
}

void SlamFilter::Landmark(std::string id, const vec3 &relpos, const mat3 &cov) {
    if (landmarks_.find(id) == landmarks_.end()) {
        NewLandmark(id, relpos, cov);
    }
    else {
        UpdateLandmark(id, relpos, cov);
    }
}

std::ostream& operator<<(std::ostream &os, const SlamFilter &sf) {
    for (int i = 0; i < sf.num_particles_; ++i) {
        os << "Particle " << i << ":" << std::endl;
        os << sf.particles_.at(i);
        os << "=================" << std::endl;
    }
    return os;
}


void SlamFilter::NewLandmark(std::string id, const vec3 &relpos, const mat3 &cov) {
    for (int i = 0; i < num_particles_; ++i) {
        particles_.at(i).AddLandmark(id, relpos, cov);
    }
    landmarks_.insert(id);
}

void SlamFilter::UpdateLandmark(std::string id, const vec3 &relpos, const mat3 &cov) {
    float certainty = exp(-1*cov.trace()/3);
    for (int i = 0; i < particles_.size(); ++i) {
        particles_.at(i).UpdateLandmark(id, relpos);
        float w = particles_.at(i).UpdateWeight(id, relpos, certainty);
        weights_[i] = w;
    }
    NormalizeWeights();
    Resample();
}

void SlamFilter::NormalizeWeights() {
    float sum = std::accumulate(weights_.begin(), weights_.end(), 0.);
    for (int i = 0; i < weights_.size(); ++i) {
        weights_[i] /= sum;
        particles_.at(i).weight_ = weights_[i];
    }
}

void SlamFilter::Resample() {
    std::vector<SlamParticle> old_particles= particles_;
    std::vector<float> old_weights = weights_;

    std::discrete_distribution<int> multi(weights_.begin(), weights_.end());

    for (int i = 0; i < particles_.size(); ++i) {
        int sampled = multi(gen_);
        particles_[i] = old_particles[sampled];
        particles_[i].ReinitRandom();
        weights_[i] = old_weights[sampled];
    }
}
