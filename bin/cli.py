#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from binascii import hexlify, unhexlify
from ConfigParser import ConfigParser
from optparse import OptionParser
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
import bna

class Authenticator(object):
	def __init__(self, args):
		options = OptionParser()
		options.add_option("-u", "--update", action="store_true", dest="update", help="update token every time")
		options.add_option("-n", "--new", action="store_true", dest="new", help="request a new authenticator")
		options.add_option("-r", "--region", type="string", dest="region", default="US", help="desired region for new authenticators")
		options.add_option("--set-default", action="store_true", dest="setdefault", help="set authenticator as default (also works when requesting a new authenticator)")
		args, serial = options.parse_args(args)
		
		self.config = ConfigParser()
		self.config.read([os.path.join(self.getConfigDir(), "bna.conf")])
		
		# Are we requesting a new authenticator?
		if args.new:
			self.queryNewAuthenticator(args)
			exit()
		
		if not serial:
			serial = self.getDefaultSerial()
			if serial is None:
				self.error("You must provide an authenticator serial")
		else:
			serial = serial[0]
		serial = bna.normalizeSerial(serial)
		
		# Are we setting a serial as default?
		if args.setdefault:
			self.setDefaultSerial(serial)
		
		# Get the secret from the keyring
		secret = self.getSecret(serial)
		if secret is None: # No such serial
			self.error("%r: No such serial" % (serial))
		
		# And print the token
		if args.update:
			self.runLive(secret)
		
		else:
			token, timeRemaining = bna.getToken(secret=unhexlify(secret))
			print(token)
	
	def error(self, txt):
		sys.stderr.write("Error: %s\n" % (txt))
		exit(1)
	
	def queryNewAuthenticator(self, args):
		try:
			authenticator = bna.requestNewSerial(args.region)
		except bna.HTTPError as e:
			self.error("Could not connect: %s" % (e))
		
		serial = bna.normalizeSerial(authenticator["serial"])
		secret = hexlify(authenticator["secret"])
		
		self.setSecret(serial, secret)
		
		# We set the authenticator as default if we don't have one set already
		# Otherwise, we check for --set-default
		if args.setdefault or not self.getDefaultSerial():
			self.setDefaultSerial(serial)
		
		print(authenticator["serial"])
	
	def runLive(self, secret):
		from time import sleep
		print("Ctrl-C to exit")
		while 1:
			token, timeRemaining = bna.getToken(secret=unhexlify(secret))
			sys.stdout.write("\r%08i" % (token))
			sys.stdout.flush()
			sleep(1)
	
	def getConfigDir(self):
		"""
		Gets the path to the config directory
		"""
		configdir = "bna"
		if os.name == "posix":
			home = os.environ.get("HOME")
			base = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
			path = os.path.join(base, configdir)
		elif os.name == "nt":
			base = os.environ["APPDATA"]
			path = os.path.join(base, configdir)
		else:
			raise NotImplementedError("Config dir support not implemented for %s platform" % (os.name))
		
		if not os.path.exists(path):
			os.makedirs(path)
		return path
	
	def getDefaultSerial(self):
		if not self.config.has_section("bna"):
			return None
		return self.config.get("bna", "default_serial")

	def setDefaultSerial(self, serial):
		if not self.config.has_section("bna"):
			self.config.add_section("bna")
		self.config.set("bna", "default_serial", serial)
		
		with open(os.path.join(self.getConfigDir(), "bna.conf"), "w") as f:
			self.config.write(f)
	
	def getSecret(self, serial):
		if not self.config.has_section(serial):
			return None
		
		return self.config.get(serial, "secret")

	def setSecret(self, serial, secret):
		if not self.config.has_section(serial):
			self.config.add_section(serial)
		self.config.set(serial, "secret", secret)
		
		with open(os.path.join(self.getConfigDir(), "bna.conf"), "w") as f:
			self.config.write(f)

def main():
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	authenticator = Authenticator(sys.argv[1:])

if __name__ == "__main__":
	main()