#ifndef SERVICEAPP_PLAYBACKPROFILE_H
#define SERVICEAPP_PLAYBACKPROFILE_H

#include <algorithm>
#include <cctype>
#include <string>

// Legacy is deliberately the default: existing installations keep their policy.
enum PlaybackProfile { PROFILE_LEGACY, PROFILE_AUTO, PROFILE_TS, PROFILE_HLS, PROFILE_VOD };

inline int playbackProfile(const std::string &name)
{
	if (name == "legacy") return PROFILE_LEGACY;
	if (name == "auto") return PROFILE_AUTO;
	if (name == "ts") return PROFILE_TS;
	if (name == "hls") return PROFILE_HLS;
	if (name == "vod") return PROFILE_VOD;
	return -1;
}

inline int effectivePlaybackProfile(int profile, const std::string &uri)
{
	if (profile != PROFILE_AUTO) return profile;
	std::string path = uri.substr(0, uri.find_first_of("?#"));
	std::transform(path.begin(), path.end(), path.begin(),
		[](unsigned char c) { return std::tolower(c); });
	// Do not mistake local recordings or a query parameter for live IPTV.
	if (path.find("http://") != 0 && path.find("https://") != 0)
		return PROFILE_VOD;
	size_t slash = path.find('/', path.find("://") + 3);
	if (slash == std::string::npos) return PROFILE_VOD;
	path = path.substr(slash);
	if (path.size() >= 5 && path.compare(path.size() - 5, 5, ".m3u8") == 0)
		return PROFILE_HLS;
	if (path.size() >= 3 && path.compare(path.size() - 3, 3, ".ts") == 0)
		return PROFILE_TS;
	return PROFILE_VOD; // Unknown/token-only URLs need an explicit profile.
}

struct PlaybackProfileSettings
{
	int profile;
	int tsBufferSize, tsBufferDuration, hlsBufferSize, hlsBufferDuration;
	bool hlsExplorer;
	PlaybackProfileSettings(): profile(PROFILE_LEGACY), tsBufferSize(8192),
		tsBufferDuration(0), hlsBufferSize(8192), hlsBufferDuration(0), hlsExplorer(false) {}
};

#endif
