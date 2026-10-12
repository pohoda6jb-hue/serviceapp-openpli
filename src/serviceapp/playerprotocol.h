#ifndef SERVICEAPP_PLAYERPROTOCOL_H
#define SERVICEAPP_PLAYERPROTOCOL_H
#include <string>
#include <vector>
class PlayerJsonLines {
    std::string pending;
    bool discard;
public:
    PlayerJsonLines(): discard(false) {}
    std::vector<std::string> append(const std::string &chunk) {
        std::vector<std::string> lines;
        for (char c : chunk) {
            if (c == '\n') {
                if (!discard && !pending.empty() && pending.front() == '{' && pending.back() == '}')
                    lines.push_back(pending);
                pending.clear(); discard = false;
            } else if (!discard && c != '\r') {
                if (pending.size() == 65536) { pending.clear(); discard = true; }
                else pending += c;
            }
        }
        return lines;
    }
};
#endif
