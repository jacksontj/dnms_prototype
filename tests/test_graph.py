import dnms.graph

import unittest


class BaseGraphTestCase(unittest.TestCase):
    def setUp(self):
        self.graph = dnms.graph.NetworkGraph()

    def _verify_graph(self, **kwargs):
        '''Verify the graph given maps of key -> count of the items in it
        '''
        fields = ('nodes', 'links', 'routes')
        for field in fields:
            # if we weren't asked to check that field, skip it
            if kwargs.get(field) is None:
                continue
            expected_map = kwargs[field]
            # make sure there are the same keys
            self.assertEqual(
                set(expected_map.keys()),
                set(getattr(self.graph, field).keys()),
                'Mismatch of {0}: expected={1} actual={2}'.format(
                    field,
                    set(expected_map.keys()),
                    set(getattr(self.graph, field).keys()),
                ),
            )

            # make sure the refcounts are correct
            for key, expected_count in expected_map.iteritems():
                self.assertEqual(
                    expected_count,
                    getattr(self.graph, field)[key].count,
                    'Mismatched refcounts of {0}.{1} expected={2} actual={3}'.format(
                        field,
                        key,
                        expected_count,
                        getattr(self.graph, field)[key].count,
                    ),
                )

    def test_nodes(self):
        nodes = {
            '192.168.1.1': 2,
            '192.168.1.2': 1,
        }

        for addr, count in nodes.iteritems():
            for x in xrange(count):
                self.graph.add_node(addr)
        self._verify_graph(nodes=nodes)

    def test_links(self):
        links = {
            ('a', 'b'): 2,
            ('b', 'c'): 1,
        }

        nodes = {
            'a': 2,
            'b': 3,
            'c': 1,
        }

        for link, count in links.iteritems():
            for x in xrange(count):
                self.graph.add_link(*link)

        self._verify_graph(links=links, nodes=nodes)

    def test_routes(self):
        routes = {
            (('a', 1), ('z', 1)): [
                'a',
                'b',
                'c',
                'z',
            ],
        }
        expected_routes = {
            (('a', 1), ('z', 1)): 1,
        }

        expected_links = {
            ('a', 'b'): 1,
            ('b', 'c'): 1,
            ('c', 'z'): 1,
        }

        expected_nodes = {
            'a': 1,
            'z': 1,
            # these are 2 since multiple links reference the node
            'b': 2,
            'c': 2,
        }

        for route_key, route in routes.iteritems():
            self.graph.add_route(route_key[0], route_key[1], route)

        self._verify_graph(
            routes=expected_routes,
            links=expected_links,
            nodes=expected_nodes,
        )

        # lets replace the route with a different one
        routes = {
            (('a', 1), ('z', 1)): [
                'a',
                'z',
            ],
        }
        expected_routes = {
            (('a', 1), ('z', 1)): 1,
        }

        expected_links = {
            ('a', 'z'): 1,
        }

        expected_nodes = {
            'a': 1,
            'z': 1,
        }
        for route_key, route in routes.iteritems():
            self.graph.add_route(route_key[0], route_key[1], route)

        self._verify_graph(
            routes=expected_routes,
            links=expected_links,
            nodes=expected_nodes,
        )
