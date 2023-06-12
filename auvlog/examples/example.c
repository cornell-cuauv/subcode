#include <auvlog/logger.h>

int main() {
    auvlog_init(AUV_DEBUG);
    auvlog_debug("hello world");
    auvlog_debugf("hello %s", "world");
    auvlog_info("hello world");
    auvlog_infof("hello %s", "world");
    auvlog_warning("hello world");
    auvlog_warningf("hello %s", "world");
    auvlog_error("hello world");
    auvlog_errorf("hello %s", "world");
    return 0;
}
