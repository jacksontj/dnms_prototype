import time

import tornado.gen
import tornado.ioloop

import dnms.udp.server
import dnms.agent


PORT_NUM = 5000



def main():
    '''Do the thing
    '''
    ioloop = tornado.ioloop.IOLoop.instance()

    # start up the PongServer, he just responds to pings
    server = dnms.udp.server.PongServer()
    server.bind(PORT_NUM)
    server.start()

    agent = dnms.agent.DNMSAgent()

    agent.add_peer('localhost')

    agent.start()


    ioloop.start()


if __name__ == '__main__':
    main()
