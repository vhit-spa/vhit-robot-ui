from socketserver import ThreadingMixIn, UnixStreamServer


class ThreadingUnixHTTPServer(ThreadingMixIn, UnixStreamServer):
    daemon_threads = True

    def get_request(self):
        request, _ = super().get_request()
        return request, ("local", 0)