serviceapp [![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html) [![serviceapp](https://github.com/OpenVisionE2/serviceapp/actions/workflows/serviceapp.yml/badge.svg)](https://github.com/OpenVisionE2/serviceapp/actions/workflows/serviceapp.yml) [![ovbot](https://github.com/OpenVisionE2/serviceapp/actions/workflows/ovbot.yml/badge.svg)](https://github.com/OpenVisionE2/serviceapp/actions/workflows/ovbot.yml)
==========
serviceapp service for enigma2
1) opravu MP3 software decoding GUI bug (dts_swdecoding -> mp3_swdecoding),
2) podporu string options v ExtEplayer3Options::update,
3) nové konfigurační volby a menu/profily pro Live TS, HLS, VOD/Auto,
4) zpřístupnění relevantních skrytých voleb live_ts, progressive, nice, mpegts_program_id, ffmpeg_option a GstPlayer ring_buffer_maxsize/download_buffer_path tam, kde dávají smysl,
5) oddělené TS/HLS buffery a reconnect/timeout strategii pokud to aktuální exteplayer3/gstplayer rozhraní reálně podporuje; nevymýšlej neexistující CLI přepínače bez ověření,
6) zachovat bezpečné defaulty a backward compatibility,
7) HLS Explorer ponechat volitelný a preferovat nativní přehrávačový HLS handling,
