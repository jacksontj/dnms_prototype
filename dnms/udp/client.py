import tornado.iostream
import tornado.ioloop
import tornado.concurrent
import tornado

import time
import socket
import functools
import collections


class UDPRequest(object):
    def __init__(self, addr, port, data, src_port=0):
        self.addr = addr
        self.port = port
        self.data = data

        self.src_port = src_port


class _UDPConnection(object):
    def __init__(self, io_loop, request, release_callback, future, max_buffer_size):
        self.start_time = time.time()
        self.io_loop = io_loop
        self.request = request
        self.release_callback = release_callback
        self.future = future

        addrinfo = socket.getaddrinfo(
            request.addr,
            request.port,
            socket.AF_INET,
            socket.SOCK_DGRAM,
            0,
            0,
        )
        af, socktype, proto, canonname, sockaddr = addrinfo[0]
        sock = socket.socket(af, socktype, proto)
        if request.src_port:
            sock.bind(('0.0.0.0', request.src_port))
        self.stream = tornado.iostream.IOStream(
            sock,
            io_loop=self.io_loop,max_buffer_size=2500,
        )
        self.stream.connect(sockaddr,self._on_connect)

    def _on_connect(self):
        self.stream.write(self.request.data)
        # TODO: buf size?
        self.stream.read_bytes(1024, partial=True, callback=self._on_response)

    def _on_response(self,data):
        if self.release_callback is not None:
            release_callback = self.release_callback
            self.release_callback = None
            release_callback()
        if self.future:
            self.future.set_result(data)
        self.stream.close()


class AsyncUDPClient(object):
    def __init__(self, io_loop=None):
        self.io_loop = io_loop or tornado.ioloop.IOLoop.instance()
        self.max_clients = 10
        self.queue = collections.deque()
        self.active = {}
        self.max_buffer_size = 2500

    # TODO: timeout
    def fetch(self, request, **kwargs):
        future = tornado.concurrent.Future()
        self.queue.append((request, future))
        self._process_queue()
        return future

    def _process_queue(self):
        with tornado.stack_context.NullContext():
            while self.queue and len(self.active) < self.max_clients:
                request, future = self.queue.popleft()
                key = object()
                self.active[key] = (request, future)
                _UDPConnection(
                    self.io_loop,
                    request,
                    functools.partial(self._release_fetch,key),
                    future,
                    self.max_buffer_size,
                )

    def _release_fetch(self,key):
        del self.active[key]
        self._process_queue()
