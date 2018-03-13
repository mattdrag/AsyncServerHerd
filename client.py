import asyncio
import sys
import server_utils as utils

#https://docs.python.org/3/library/asyncio-protocol.html
class EchoClientProtocol(asyncio.Protocol):
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

def main():
	# first check arguments to make sure server was initialized correctly
	if len(sys.argv) != 3:
		sys.stdout.write('Invalid number of args')
		exit(1)

	message = sys.argv[1]
	target_server = sys.argv[2]

	port = utils.getPort(target_server)

	loop = asyncio.get_event_loop()
	coro = loop.create_connection(lambda: EchoClientProtocol(message, loop),
	                              '127.0.0.1', port)
	loop.run_until_complete(coro)


if __name__ == "__main__":
	main()