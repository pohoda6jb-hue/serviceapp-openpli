#ifndef SERVICEAPP_RECOVERY_H
#define SERVICEAPP_RECOVERY_H

// No URL heuristic may turn an ordinary VOD EOF into a live restart.
class LiveRecovery
{
    bool enabled, stopped, pending;
    unsigned attempts, limit;
public:
    LiveRecovery(): enabled(false), stopped(false), pending(false), attempts(0), limit(5) {}
    void configure(bool live, unsigned retries) { enabled = live; limit = retries; }
    unsigned processExited()
    {
        if (!enabled || stopped || pending || attempts >= limit) return 0;
        pending = true;
        ++attempts;
        return 2000 * (attempts > 5 ? 5 : attempts);
    }
    bool consumeRetry()
    {
        if (stopped || !pending) return false;
        pending = false;
        return true;
    }
    void stop() { stopped = true; pending = false; }
    bool isStopped() const { return stopped; }
    bool isPending() const { return pending; }
};
#endif
