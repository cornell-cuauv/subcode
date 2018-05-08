#ifndef SLAM_FILTER
#define SLAM_FILTER
#include "ekf.h"
#include <vector>
#include <unordered_map>
#include <unordered_set>

#define dt .1

class SlamParticle {
    public:
        float weight_;

    private:
        vec3 position_;
        vec3 orientation_;

        std::unordered_map<std::string, SlamEKF> landmark_filters_;

    public:
        SlamParticle(float weight, const vec3 &pos, const vec3 &ori);
        void AddLandmark(std::string id, const vec3 &relpos, const mat3 &conv);
        void UpdateLandmark(std::string id, const vec3 &relpos);
        void UpdateParticle(const vec6 &u, float weight);
        float UpdateWeight(std::string id, const vec3 &relpos, float certainty);
        vec3 GetState();
        vec3 GetState(std::string id);

};

class SlamFilter {
    private:
        std::vector<SlamParticle> particles_;
        std::vector<float> weights_;
        std::unordered_set<std::string> landmarks_;
        int num_particles_;

    public:
        SlamFilter(int n);
        SlamFilter(int n, const vec3 &pos, const vec3 &ori);
        void Update(const vec6 &u);
        void Landmark(std::string, const vec3 &realpos, const mat3 &cov);

    private:
        void NewLandmark(std::string id, const vec3 &relpos, const mat3 &cov);
        void UpdateLandmark(std::string id, const vec3 &relpos, float certainty);
        void NormalizeWeights();
        void Resample();

};

#endif
