# SF8008 live recovery experiment

Target: OpenPLi 9.2, ARM SF8008, Python 3.9, FFmpeg 4.4.3. The artifact
contains two runtime packages: ServiceApp and exteplayer3. No FFmpeg/image
upgrade is included. Keep the feed versions available for rollback.

## Changes and limits

* Recovery is OFF by default. In Extensions → ServiceApp: current stream,
  explicitly mark a stream Live and choose exteplayer3. TS/HLS URL suffixes
  do not prove that a stream is live. Explicit VOD profile disables recovery.
* Default budget: five process restarts, delayed 2, 4, 6, 8 and 10 seconds.
  The budget lasts until leaving the service. Successful startup does not reset
  it, avoiding infinite loops. Manual stop/zapping cancels pending retries.
* This handles process termination, not a player process hung indefinitely.
  No unverified frozen-picture watchdog or unlimited retry is claimed.
* Saved channel options override global settings/profiles; URL `sapp_` options
  override saved options. Settings apply on the next opening of the stream.
  The JSON file stores SHA256 URL identities, not original stream credentials.
  Identical URLs share preferences. A changed token changes the identity.
* HLS Explorer is optional per stream. Fetching runs in an independent worker;
  results from stopped services are discarded. At most two workers run at once.
  Slow DNS may outlive cancellation, but never blocks the Enigma main thread.
  External audio/video/subtitle rendition groups cause fallback to native HLS.
* exteplayer3 retains OpenPLi defaults, but explicit `-f` HTTP settings are no
  longer overwritten. No new CLI switches were invented. Read failures carry
  a numeric FFmpeg code; exit status is logged by ServiceApp.
* This is not full FFmpeg reconnect-progress telemetry: internal HTTP retries
  cannot yet be reliably reported as reconnecting/reconnected states.

## Receiver validation

1. Verify both package versions after installation and restart Enigma through
   its menu. The modified ServiceApp version starts with `1+git178+openplits`.
2. On one live TS and one live HLS channel, select exteplayer3, matching profile,
   Live recovery, Native player HLS. Save, then leave and reopen the channel.
3. Record startup time and `pidof exteplayer3`. Disconnect networking for 30 s,
   reconnect, record recovery time, new PID, sound/image sync, and logs.
4. Repeat with 5 s and 60 s outages. During recovery, switch to another channel
   and verify that the abandoned channel never resumes or steals playback.
5. Stop playback during a scheduled retry. No new player process may appear.
6. Use a finite VOD clip, including HLS with ENDLIST. At normal EOF no restart
   may occur. Explicit VOD profile takes precedence over accidental Live marking.
7. Test HLS master with separate audio and variant changes. Both audio and video
   must play; Explorer must preserve master handling for external renditions.
8. With a permanently unavailable live URL, verify exhaustion of the configured
   retry budget. Manual reopening starts a fresh budget.

Receiver results are still required; host unit tests and compilation do not
establish hardware playback quality or distribution acceptance.

Upstream basis: oe-mirrors/exteplayer3 e258b47863fae1d74dbd1d707c948ae4232fea64.
The complete player changes are in exteplayer3-live.patch; the build pins this
revision. Review and test before proposing separate upstream/distribution PRs.
