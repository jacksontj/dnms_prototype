import socket


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
