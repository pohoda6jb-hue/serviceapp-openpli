"""Exercise the production HLS parser against local HTTP fixtures on Linux."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading

root = Path(__file__).resolve().parents[1]
fixtures = {
    '/master.m3u8': '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\nvideo.m3u8\n',
    '/separate.m3u8': '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,AUDIO="sound"\nvideo.m3u8\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="sound",URI="audio.m3u8"\n',
    '/media.m3u8': '#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:1\n#EXTINF:4,\nsegment.ts\n',
    '/long.m3u8': '#EXTM3U\n#' + 'x' * 70000 + '\n',
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = fixtures[self.path].encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def log_message(self, *args):
        pass

with tempfile.TemporaryDirectory() as temporary:
    runner = Path(temporary) / 'runner.cpp'
    runner.write_text('#include "m3u8.h"\n#include <iostream>\nint main(int n,char**v){M3U8VariantsExplorer e(v[1],HeaderMap());std::cout<<e.getStreams().size()<<"\\n";}\n')
    binary = Path(temporary) / 'hls'
    sources = [root / 'src/serviceapp' / name for name in ('m3u8.cpp', 'wrappers.cpp', 'common.cpp')]
    subprocess.run(['g++', '-std=c++17', '-DNO_PYTHON', '-DNO_UCHARDET', '-I' + str(root / 'src/serviceapp'),
                    str(runner), *map(str, sources), '-lssl', '-lcrypto', '-o', str(binary)], check=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for path, expected in (('/master.m3u8', 1), ('/separate.m3u8', 0), ('/media.m3u8', 0), ('/long.m3u8', 0)):
            result = subprocess.run([str(binary), 'http://127.0.0.1:%d%s' % (server.server_port, path)],
                                    text=True, capture_output=True, timeout=15, check=True)
            assert int(result.stdout.strip()) == expected, (path, result.stdout, result.stderr)
        print('Production HLS parser: variants, rendition fallback, media playlist and line limit passed')
    finally:
        server.shutdown()
        server.server_close()
