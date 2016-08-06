#!/usr/bin/python

import pprint
pp = pprint.PrettyPrinter(indent=4)

import optparse
import socket
import sys


def traceroute(dest_addr, dst_port, max_hops, src_port=None):
    '''Return route for dest_addr
    '''
    route = []
    ttl = 1
    while True:
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname('icmp'))
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.getprotobyname('udp'))
        send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
        if src_port:
            send_socket.bind(("0.0.0.0", src_port))
        recv_socket.bind(("", dst_port))
        # don't listen forever
        recv_socket.settimeout(2)  # TODO arg?
        send_socket.sendto(" ", (dest_addr, dst_port))
        curr_addr = None
        try:
            # socket.recvfrom() gives back (data, address), but we
            # only care about the latter.
            # TODO: verify the ICMP response is from the thing we just sent!
            _, curr_addr = recv_socket.recvfrom(512)
            curr_addr = curr_addr[0]  # address is given as tuple
        except socket.error:
            pass
        finally:
            send_socket.close()
            recv_socket.close()

        if curr_addr is not None:
            curr_host = "%s" % (curr_addr)
        else:
            curr_host = "*"
        route.append(curr_addr)

        ttl += 1
        if curr_addr == dest_addr or ttl > max_hops:
            break

    return tuple(route)


# TODO parallelize
def all_routes(dest, start_port, end_port, max_hops):
    '''
    Map all possible routes to dest through the port ranges
    '''
    dest_addr = socket.gethostbyname(dest)
    # TODO: check that end_port is after start_port, and within a reasonable range
    # mapping of port -> route
    routes = {}
    # route -> ports
    reverse_routes = {}
    print 'mapping %s -> %s' % (start_port, end_port)
    for port in xrange(start_port, end_port):
        print 'mapping %s' % port
        route = traceroute(dest_addr, port, max_hops, src_port=5555)
        routes[port] = route
        if route not in reverse_routes:
            reverse_routes[route] = set()
        reverse_routes[route].add(port)

    pp.pprint(routes)
    pp.pprint(reverse_routes)
    return routes, reverse_routes


if __name__ == "__main__":
    parser = optparse.OptionParser(usage="%prog [options] hostname")
    parser.add_option("-m", "--max-hops", dest="max_hops",
                      help="Max hops before giving up [default: %default]",
                      default=30, metavar="MAXHOPS")
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error('')
    else:
        dest = args[0]
    sys.exit(
        all_routes(
            dest=dest,
            start_port=33434,
            end_port=33437,
            max_hops=int(options.max_hops),
        ),
    )
