import pprint


class NetworkNode(object):
    def __init__(self, addr):
        self.addr = addr
        # refcount
        self.count = 0
    def __repr__(self):
        return pprint.pformat(vars(self))


class Link(object):
    def __init__(self, src_node, dst_node):
        self.src = src_node
        self.dst = dst_node
        self.count = 0
    def __repr__(self):
        return pprint.pformat(vars(self))

class Route(object):
    def __init__(self, src_tup, dst_tup, route, links):
        self.src_tup = src_tup
        self.dst_tup = dst_tup
        self.route = route
        # list of links
        self.links = links
        self.count = 0
    def __repr__(self):
        return pprint.pformat(vars(self))


class NetworkGraph(object):
    '''Graph of the network

    This is where most of the magic happens.

    This graph consists of:
        - NetworkNodes: L3 devices in the network, refcounted by number of links going through
        - Links: connections between various NetworkNodes, refcounted by number of routes that use it

    This graph is dynamic based on the results of various traceroutes. Specifically
    this means that the nodes and edges of this graph are refcounted, and can change
    over time

    Relationships

        NetworkNode

        Link
            2 NetworkNodes

        Route
            set of links

    '''
    def __init__(self):

        # key -> object
        self.nodes = {}
        self.links = {}

        # (ip, port)*src -> (ip, port)*dst -> object
        self.routes = {}

    def __repr__(self):
        return pprint.pformat(vars(self))

    def add_node(self, addr):
        if addr not in self.nodes:
            self.nodes[addr] = NetworkNode(addr)
        self.nodes[addr].count += 1
        return self.nodes[addr]

    def rm_node(self, addr):
        # TODO: warning!
        if addr not in self.nodes:
            return
        self.nodes[addr].count -= 1
        if self.nodes[addr].count == 0:
            del self.nodes[addr]

    def add_link(self, src_addr, dst_addr):
        link_key = (src_addr, dst_addr)
        # if the link doesn't exist, lets create it
        if link_key not in self.links:
            src = self.add_node(src_addr)
            dst = self.add_node(dst_addr)
            self.links[link_key] = Link(src, dst)
        # otherwise we simply bump the refcounts
        else:
            self.add_node(self.links[link_key].src.addr)
            self.add_node(self.links[link_key].dst.addr)

        self.links[link_key].count += 1
        return self.links[link_key]

    def rm_link(self, src_addr, dst_addr):
        link_key = (src_addr, dst_addr)
        # TODO: log warning!
        if link_key not in self.links:
            return

        link = self.links[link_key]

        # decrememnt src and dst
        # TODO: check that they are the same??
        self.rm_node(src_addr)
        self.rm_node(dst_addr)

        link.count -= 1
        if link.count == 0:
            del self.links[link_key]

    def add_route(self, src_tup, dst_tup, route):
        old_route = None
        route_key = (src_tup, dst_tup)
        # if the route exists, does it match?
        if route_key in self.routes:
            # if they match, bump the refcount and move on
            if self.routes[route_key].route == route:
                self.routes[route_key].count += 1
                return self.routes[route_key]
            # if they don't match remove it
            else:
                old_route = self.routes.pop(route_key)

        # if its a new route -- do that
        if route_key not in self.routes:
            links = []
            for i, link in enumerate(route):
                next_i = i + 1
                if next_i >= len(route):
                    break
                links.append(self.add_link(route[i], route[next_i]))
            self.routes[route_key] = Route(
                src_tup,
                dst_tup,
                tuple(route),
                tuple(links),
            )
        self.routes[route_key].count += 1

        if old_route is not None:
            for link in old_route.links:
                self.rm_link(link.src.addr, link.dst.addr)

        return self.routes[route_key]

    def remove_route(self, src_tup, dst_tup, route):
        route_key = (src_tup, dst_tup)
        # TODO: log warning!
        if route_key not in self.routes:
            return

        route = self.routes[route_key]
        # decrement all the links
        for link in route.links:
            self.rm_link(link.src, link.dst)

        # decrement route
        route.count -= 1
        if route.count == 0:
            del self.routes[route_key]
