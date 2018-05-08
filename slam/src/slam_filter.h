#ifndef SLAM_FILTER
#define SLAM_FILTER
#include "ekf.h"
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <random>
#include <iostream>

#define dt .25

class SlamParticle {
    public:
        float weight_;

    private:
        vec3 position_;
        vec3 orientation_;

        std::unordered_map<std::string, SlamEKF> landmark_filters_;

        std::default_random_engine gen_;
        std::normal_distribution<float> uniform_;
        std::normal_distribution<float> gaussian_;

    public:
        SlamParticle(float weight, const vec3 &pos, const vec3 &ori);
        void AddLandmark(std::string id, const vec3 &relpos, const mat3 &conv);
        void UpdateLandmark(std::string id, const vec3 &relpos);
        void UpdateParticle(const vec6 &u, float weight);
        float UpdateWeight(std::string id, const vec3 &relpos, float certainty);

        void ReinitRandom();

        vec3 GetState();
        vec3 GetState(std::string id);

        friend std::ostream& operator<<(std::ostream &os, const SlamParticle &sp);

};

class SlamFilter {
    private:
        std::vector<SlamParticle> particles_;
        std::vector<float> weights_;
        std::unordered_set<std::string> landmarks_;
        int num_particles_;

        std::default_random_engine gen_;

    public:
        SlamFilter(int n);
        SlamFilter(int n, const vec3 &pos, const vec3 &ori);
        void Update(const vec6 &u);
        void Landmark(std::string id, const vec3 &relpos, const mat3 &cov);

        vec3 GetState();
        vec3 GetState(std::string id);

        friend std::ostream& operator<<(std::ostream &os, const SlamFilter &sf);

    private:
        void NewLandmark(std::string id, const vec3 &relpos, const mat3 &cov);
        void UpdateLandmark(std::string id, const vec3 &relpos, const mat3 &cov);
        void NormalizeWeights();
        void Resample();

};

#endif
