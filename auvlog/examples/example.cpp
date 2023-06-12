#include <auvlog/logger.h>
#include <lib/fmt.h>

int main() {
    auvlog_init(AUV_DEBUG);
    auvlog_debug(fmt::format("hello {}", "world"));
    auvlog_info(fmt::format("hello {}", "world"));
    auvlog_warning(fmt::format("hello {}", "world"));
    auvlog_error(fmt::format("hello {}", "world"));
    return 0;
}
