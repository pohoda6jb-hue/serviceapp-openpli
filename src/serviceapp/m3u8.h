#ifndef __m3u8variant__h
#define __m3u8variant__h
#include <map>
#include <vector>
#include <string>
#include <sstream>
#include <atomic>
#include <chrono>

#include "wrappers.h"
#include "common.h"

struct M3U8StreamInfo
{
    std::string url;
    HeaderMap headers;
    std::string codecs;
    std::string resolution;
    // TODO audio/video/subtitles..
    unsigned long int bitrate;

    bool operator<(const M3U8StreamInfo& m) const
    {
        return bitrate < m.bitrate;
    }
};

class M3U8VariantsExplorer
{
    std::string url;
    HeaderMap headers;
    std::vector<M3U8StreamInfo> streams;
    const unsigned int redirectLimit;
    const std::atomic<bool> *cancelled;
    std::chrono::steady_clock::time_point deadline;
    int parseStreamInfoAttributes(const char *line, M3U8StreamInfo& info);
    int getVariantsFromMasterUrl(const std::string& url, HeaderMap& headers, unsigned int redirect);
public:
    M3U8VariantsExplorer(const std::string& url, const HeaderMap& headers, const std::atomic<bool> *cancelled = NULL):
        url(url),
        headers(headers),
        redirectLimit(5), cancelled(cancelled), deadline(std::chrono::steady_clock::now() + std::chrono::seconds(8)) {};
    std::vector<M3U8StreamInfo> getStreams();

};

bool isM3U8Url(const std::string& url);
#endif

