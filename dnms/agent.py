'''
'''
import tornado.ioloop
import tornado.gen

import dnms.udp.client
import dnms.traceroute
import dnms.graph

import concurrent.futures
import time
import socket


# TODO: move to another file!
class Peer(object):
    '''Represent a peer on the network
    '''
    def __init__(self, name=None, addr=None):
        self.name = name
        if addr is None:
            self.addr = socket.gethostbyname(name)
        else:
            self.addr = addr

        # map of route_object -> [ports]
        self.route_port_map = {}

    # TODO: maintain maps both directions?
    def get_route(self, port):
        for r, portset in self.route_port_map.iteritems():
            if port in portset:
                return r
        return None

    def set_route(self, port, new_route):
        old_route = self.get_route(port)
        # fast path
        if old_route == new_route:
            return

        if new_route not in self.route_port_map:
            self.route_port_map[new_route] = set()
        self.route_port_map[new_route].add(port)
        if old_route:
            self.route_port_map[old_route].remove(port)


class DNMSAgent(object):
    '''Main agent-- this is where the magic happens

    This agent needs to do the following:
        - traceroute: map the network
        - ping: determine what is available
    '''

    def __init__(self, ioloop=None):
        # TODO: async persist graph to disk?
        self.graph = dnms.graph.NetworkGraph()

        # TODO: better determining the IP of `self`
        self.local_peer = Peer(addr=([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]))

        # map of name -> peer_obj
        self.peers = {}
        self.started = False
        self.ioloop = ioloop if ioloop is not None else tornado.ioloop.IOLoop.current()

        # TODO: config
        #self.port_range = (33434, 33437)
        self.port_range = (33434, 33435)

        # TODO: config number of threads
        self.pool = concurrent.futures.ThreadPoolExecutor(5)

    def start(self):
        self.started = True

        # TODO: lock source ports? right now these 2 immediately conflict
        # start pinger
        #self.ioloop.spawn_callback(self.ping_peers)
        # start traceroute
        self.ioloop.spawn_callback(self.traceroute_peers)

    # TODO: move into a peer-group class?
    def add_peer(self, name):
        if name in self.peers:
            return

        self.peers[name] = Peer(name)

    def remove_peer(self, name):
        if name not in self.peers:
            return

        del self.peers[name]

    # TODO: configurable parallelism
    @tornado.gen.coroutine
    def ping_peers(self):
        '''this coroutine is responsible for pinging all the peers
        '''
        self.udp_client =  dnms.udp.client.AsyncUDPClient()
        while True:
            peers = dict(self.peers)  # make a copy

            # TODO: shuffle order
            for peer_name, peer in peers.iteritems():
                yield self.ping_peer(peer)
                yield tornado.gen.sleep(1)


    @tornado.gen.coroutine
    def ping_peer(self, peer):
        for port in xrange(*self.port_range):
            request = dnms.udp.client.UDPRequest(
                peer.addr,
                5000,  # TODO config of dst port
                str(time.time()),  # TODO: real ping message
                src_port = port,
            )
            start = time.time()
            response = yield self.udp_client.fetch(request)
            took = time.time() - start
            print 'got a response', response
            print 'took', took
            # TODO: do something with the response-- this data should be stored on
            # the route-- probably a rolling window of ping responses (success/fail and latency)
            yield tornado.gen.sleep(1)
            x += 1


    # TODO: configurable parallelism
    @tornado.gen.coroutine
    def traceroute_peers(self):
        old_graph = None
        while True:
            peers = dict(self.peers)  # make a copy

            # TODO: shuffle order
            for peer_name, peer in peers.iteritems():
                print 'tracing peer'
                yield self.traceroute_peer(peer)
                # TODO: configurable sleep
                yield tornado.gen.sleep(5)
            new_graph = str(self.graph)
            if old_graph != new_graph:
                print new_graph
                old_graph = new_graph
            else:
                print 'no change to graph'

    @tornado.gen.coroutine
    def traceroute_peer(self, peer):
        dst_addr = (peer.addr, 5000)
        for port in xrange(*self.port_range):
            print 'tracing peer from port', port
            raw_route = yield self.pool.submit(
                dnms.traceroute.traceroute,
                peer.addr,
                5000,  # TODO config of dst port
                3,  # TODO: config number of hops
                src_port=port
            )
            # TODO: validate the new_route (since the traceroute could be broken)
            old_route = peer.get_route(port)

            # if there wasn't a route before or if it has changed, lets set it
            if (old_route is None or (old_route is not None and old_route.route != tuple(raw_route))):
                new_route = self.graph.add_route(
                    (self.local_peer.addr, port),
                    dst_addr,
                    raw_route,
                )
                peer.set_route(port, new_route)
            yield tornado.gen.sleep(5)
