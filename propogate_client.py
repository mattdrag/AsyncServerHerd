import asyncio
import sys
import server_utils as utils

#https://docs.python.org/3/library/asyncio-protocol.html
class PropogateClientProtocol(asyncio.Protocol):
	def __init__(self, message, loop):
		self.message = message
		self.loop = loop

	def connection_made(self, transport):
		transport.write(self.message.encode())
		print('Data sent: {!r}'.format(self.message))

	def data_received(self, data):
		print('Data received: {!r}'.format(data.decode()))

	def connection_lost(self, exc):
		print('The server closed the connection')
		print('Stop the event loop')
		self.loop.stop()

async def main(message, server):

	port = utils.getPort(server)

	loop = asyncio.get_event_loop()
	coro = loop.create_connection(lambda: PropogateClientProtocol(message, loop),
	                              '127.0.0.1', port)
	asyncio.ensure_future(coro)
