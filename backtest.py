#!/usr/bin/env python

import sys
import os
import itertools
import collections
from datetime import datetime
import csv
import decimal
D = decimal.Decimal
decimal.getcontext().prec = 6

class InvalidOrderException(Exception): pass
class InvalidStateException(Exception): pass
class InvalidBarException(Exception): pass
class InvalidLevelException(Exception): pass

###
# Basic bar object
# 
# pass a string containing the data representing the bar
#
# contains the basic data open/high/low/close date & time.
###
class Bar(object):

	def __init__(self, sym, str):

		#20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506
		#(dt, self.symbol, self.op, self.hi, self.lo, self.cl) = str.split(',')
		(dt, cd, opn, hgh, lw, cls) = str.split(',')
		self.date = datetime(int(dt[0:4]), int(dt[4:6]), int(dt[6:8]), int(dt[9:11]))
		self.symbol = sym
		#self.op = float(opn)
		#self.hi = float(hgh)
		#self.lo = float(lw)
		#self.cl = float(cls)
		self.op = D(opn)
		self.hi = D(hgh)
		self.lo = D(lw)
		self.cl = D(cls)


	def __merge_bar(self, b):
		"""aggregate the high, low and close of a new bar. The timestamp will remain the same, the close will be updated to the new bar"""

		if b.hi > self.hi:
			self.hi = b.hi
		if b.lo < self.lo:
			self.lo = b.lo
		self.cl = b.cl

	def merge(self, c, h=None, l=None):
		"""aggregate a high low and close"""

		if isinstance(c, Bar):
			return(self.__merge_bar(c))
	
		if not h is None and h > self.hi:
			self.hi = h 
		if not l is None and l < self.lo:
			self.lo = l 
		self.cl = c 

	def __str__(self):
		return "Bar: %s,%s,%.4f,%.4f,%.4f,%.4f" % (self.date.strftime("%Y%m%d-%H%M%S"), 
		    self.symbol, self.op, self.hi, self.lo, self.cl)

class YahooBar(Bar):

	def __init__(self, sym, str):

		#20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506
		(dt, opn, hgh, lw, cls, vol, acls) = str.split(',')
		self.date = datetime(int(dt[0:4]), int(dt[5:7]), int(dt[8:10]))
		self.symbol = sym 
		#self.op = float(opn)
		#self.hi = float(hgh)
		#self.lo = float(lw)
		#self.cl = float(cls)
		self.op = D(opn)
		self.hi = D(hgh)
		self.lo = D(lw)
		self.cl = D(cls)

class Order(object):

	#type
	LIMIT = 1
	STOP = 2
	MARKET = 3

	#dir
	BUY = 1
	SELL = 2

	#state
	UNSUB = 0
	ACTIVE = 1
	PENDING = 2
	CANCELLED = 3
	FILLED = 4
	StateList = [UNSUB, ACTIVE, PENDING, CANCELLED, FILLED]

	id_iter = itertools.count(1)

	def __init__(self, symbol=None, dir=None, type=None, level=None, size=None, parent=None, link=None):
		self.id = self.id_iter.next()
		self.nbars = 0
		self.symbol = symbol
		self.type = type
		self.level = level
		self.dir = dir
		self.size = size 
		self._cancels = []
		self.cancel_parent = None
		self._triggers = []
		self.trigger_parent = parent 
		self.link = link
		self._state = Order.UNSUB

	def __get_level(self):
		return self._level
	def __set_level(self, x):
		if not x is None and not isinstance(x, decimal.Decimal):
			self._level = D(str(x))
		else:
			self._level = x 
	level = property(__get_level, __set_level)

	def __eq__(self, other):

		if self.id == other.id:
			return True
		return False		

	def __str__(self):

		s = "Order: ID=%d, %s " % (self.id, self.symbol)

		if self.dir == Order.BUY:
			s += "BUY "
		elif self.dir == Order.SELL:
			s += "SELL " 

		if self.type == Order.LIMIT:
			s += "LIMIT "
			s += "%.1f @ %.4f " % (self._size, self.level)
		elif self.type == Order.STOP:
			s += "STOP "
			s += "%.1f @ %.4f " % (self._size, self.level)
		elif self.type == Order.MARKET:
			s += "MARKET "
			if self.level is None:
				s += "%.1f @ <MKT> " % (self._size)
			else:
				s += "%.1f @ %.4f " % (self._size, self.level)
	

		if self.state == Order.UNSUB:
			s += "UNSUB "
		elif self.state == Order.ACTIVE:
			s += "ACTIVE "	
		elif self.state == Order.PENDING:
			s += "PENDING "	
		elif self.state == Order.CANCELLED:
			s += "CANCELLED "	
		elif self.state == Order.FILLED:
			s += "FILLED "	

		s += "%d triggers, %d cancels" % (len(self._triggers), len(self._cancels))

		return(s)

	def __set_state(self, state):
		if not state in Order.StateList:
			raise InvalidStateException("Unknown Order State '%s'" % state)
		self._state = state
	def __get_state(self):
		return self._state
	state = property(__get_state, __set_state)
		
	def __get_size(self):
		return self._size

	def __set_size(self, sz):
		if self.dir != Order.BUY and self.dir != Order.SELL and sz != None:
			raise InvalidOrderException("you must set an order direction before setting size")

		#i wonder if i should make these exceptions
		if self.dir == Order.BUY and sz < 0:
			raise InvalidOrderException("Order to buy negative amount of shares")
			#print "Order %d %s BUY %.1f: negative BUY changed to SELL" % (self.id, self.symbol, sz)
			#self.dir = Order.SELL
		elif self.dir == Order.SELL and sz > 0:
			raise InvalidOrderException("Order to sell positive amount of shares")
			#print "Order %d %s SELL: flipping sell size to negative %.1f" % (self.id, self.symbol, sz)
			#sz = -sz

		self._size = sz

	size = property(__get_size, __set_size)

	def cancel(self, order):
		if isinstance(order, collections.Iterable):
			for o in order:
				self._cancels.append(o.id)
				o.cancel_parent = self.id
		elif isinstance(order, Order):
			self._cancels.append(order.id)
			order.cancel_parent = self.id
		else:
			raise InvalidOrderException("cancel passed unknown order class: %s" % type(order))

	def __get_cancels(self):
		return self._cancels
	cancels = property(__get_cancels)

	#not sure if this is required right now but here it is
	def is_cancelled(self):
		return self.cancel_parent != None

	#return the list of id's triggered if this order is filled
	def __get_triggers(self):
		return self._triggers
	triggers = property(__get_triggers)

	##
	# xxx redo this so 2nd arg is iterable
	# i took it out for some reason so i should check why
	##
	# add id(s) of orders to trigger if this order is filled
	# flag the triggered orders as subject to this order
	def trigger(self, order, *args):

		self._triggers.append(order.id)
		order.trigger_parent = self.id
		for o in args:
			self._triggers.append(o.id)
			o.trigger_parent = self.id

		#if isinstance(order, collections.Iterable):
		#	for o in order:
		#		self._triggers.append(o.id)
		#		o.trigger_parent = self.id
		#else:
		#	self._triggers.append(order.id)
		#	order.trigger_parent = self.id

	# returns true if an order is trigged by some other order
	def triggered(self):
		return not self.trigger_parent is None

	#xxx make this a class method
	def OCO(o1, o2):
		#passing iterables is not support at the mo
		if not isinstance(o1, Order) or not isinstance(o2, Order):
			raise InvalidOrderException("OCO called with non Order object arguments")
		o1.cancel(o2)
		o2.cancel(o1)

	def validate(order, mark):

		if order.type != Order.LIMIT and order.type != Order.SELL and order.type != Order.MARKET:
			raise InvalidOrderException("order validate: invalid order type")
		if order.level is None:
			raise InvalidOrderException("order validate: no level set")

		#check an order makes sense for the current mark level
		if order.dir == Order.BUY:
			if order.type == Order.LIMIT and order.level > mark:
				raise InvalidOrderException("Buy limit with level %.4f > current mark %.4f" % (order.level, mark))
			elif order.type == Order.STOP and order.level < mark:
				raise InvalidOrderException("Buy limit with level %.4f < current mark %.4f" % (order.level, mark))
		elif order.dir == Order.SELL:
			if order.type == Order.LIMIT and order.level < mark:
				raise InvalidOrderException("Sell limit with level %.4f < current mark %.4f" % (order.level, mark))
			elif order.type == Order.STOP and order.level > mark:
				raise InvalidOrderException("Sell limit with level %.4f > current mark %.4f" % (order.level, mark))
			
#the orderbook
class OrderBook(object):
	
	def __init__(self, debug=False):
		#self.symbol = 'OrderBook'
		self.debug = debug
		#though about a list indexed by id here but either we would
		#have a bunch of empty slots that we have to manage ourselves
		#if orders are assigned id's but not submitted
		#using a dict means we also dont make assumptions aobut the
		#repsenstation of order.id 
		self._orders = {} 
		self._done = {}

	def __str__(self):
		s = "OrderBook: Active=%d, Filled=%d, Cancelled=%d" % (
			len(self.active), len(self.filled), 
			len(self.cancelled))
		return(s)

	def __active_ids(self):
		return [oid for oid in self._orders if self._orders[oid].state == Order.ACTIVE]
	active = property(__active_ids)

	def __pending_ids(self):
		return [oid for oid in self._orders if self._orders[oid].state == Order.PENDING]
	pending = property(__pending_ids)

	def __cancelled_ids(self):
		return [oid for oid in self._done if self._done[oid].state == Order.CANCELLED]
	cancelled = property(__cancelled_ids)

	def __filled_ids(self):
		return [oid for oid in self._done if self._done[oid].state == Order.FILLED]
	filled = property(__filled_ids)

	###
	# add an order to the queue
	#
	# triggered orders must also be added, it is not enough
	# to call o1.trigger(o2) and not add o2.
	###
	#might be possible to neaten this up
	def add(self, order, *args):

		if isinstance(order, collections.Iterable):
			for o in order:
				self.add(o)
		else:
			self._add_single(order)

		for o in args:
			self.add(o)

	def _add_single(self, order):

		if not order.triggered():
			order.state = Order.ACTIVE
		else: # will only become active if its parent fills 
			order.state = Order.PENDING

		if self._orders.has_key(order.id):
			raise InvalidOrderException('duplicate order id: %d' % order.id)
		
		#need to sanity check orders, e.g. if a buy stop < cur_price
		#it would be triggered immediately
		self._orders[order.id] = order

		if self.debug:
			print "OrderBook: Added %s" % (order)
	
	def cancel_all(self):

		if self.debug:
			print "\n\nOrderBook: cancelling %d active and %d pending\n\n" % (len(self.active), len(self.pending))
		for oid in self.active + self.pending:
			#self._orders[oid].state = Order.CANCELLED
			self.cancel(oid)
			if self.debug:
				print "OrderBook: cancel_all cancelled: %s" %(oid)

	def cancel(self, order):

		if order is None: 
			return False

		if isinstance(order, Order):
			order_id = order.id
		else:
			order_id = order

		if self.debug:
			print "OrderBook: want to cancel order id: %d" % (order_id)

		if not self._orders.has_key(order_id):
			if self.debug:
				print "OrderBook: order id not found %d" % (order_id)
			return False
		
		o = self._orders[order_id]
		o.state = Order.CANCELLED
		self._done[o.id] = o
		del self._orders[o.id]
		if self.debug:
			print "OrderBook: Cancelled order id %d" % (o.id)
		#cancel any orders it would've triggered
		for oid in o.triggers:
			if self.debug:
				print "OrderBook: cancelling trig child id %d" % (oid)
			self.cancel(oid)
		return True

	###
	# mark the order as filled
	###
	def fill(self, order):

		if order is None or not self._orders.has_key(order.id):
			if self.debug:
				print "OrderBook: Fill called on nonexistent order: ", order
			return False

		if self.debug:
			print "OrderBook: book fill order id %d" % (order.id)
		o = self._orders[order.id]
		o.state = Order.FILLED
		self._done[o.id] = o
		del self._orders[o.id]
		for t in o.triggers:
			self._orders[t].state = Order.ACTIVE
			if self.debug:
				print "OrderBook: Pending -> Active %s" % (self._orders[t])
		for c in o.cancels:
			if self.debug:
				print "OrderBook: Cancelling %d coz %d filled" % (c, o.id)
			self.cancel(c)

		if self.debug:
			print "OrderBook: filled %s" % (o)
		return True

	###
	# all this will do is return what orders have been hit
	### 

	def get_fills(self, bar):

		fills = []
		#whats in the active list
		for oid in self.active: 
			o = self._orders[oid]
			#make sure the order symbol matches the sym of this bar
			if o.symbol != bar.symbol:
				continue
			if o.type == Order.MARKET:
				#fill them at the close or open ...?
				#o.level = bar.cl
				#o.level = bar.op
				#or u can enter what ever fill u want by setting 
				#the level when order placed (i.e. set it to the close)
				#this seems decidely error prone
				fills.append(o)
			elif o.level >= bar.lo and o.level <= bar.hi: #welp
				fills.append(o)
			#elif o.dir == Order.STOP:
			#	if o.dir == Order.BUY and (o.level >= b.lo and o.level <= b.hi):
			#		fills.append(o)	
			#	elif o.dir == Order.SELL and (o.level >= b.lo and o.level <= b.hi):
			#		fills.append(o)
			#elif o.dir == Order.LIMIT:
			#	if o.dir == Order.BUY and (o.level >= b.lo and o.level <= b.hi):
			#		fills.append(o)
			#	elif o.dir == Order.SELL and (o.level >= b.lo and o.level <= b.hi)
		return fills 
		
class Position(object):

	#xxx should probably raise an exception with no entry price as value depends on it
	# and positionlist depends on value
	def __init__(self, symbol=None, dt=None, entry=None, size=None, order_id=None, exit=None):
		self.symbol = symbol
		self.dt = dt #entry date/time
		self.entry = entry
		self.size = size 
		#how long open
		self.nbars = 0
		#cur price
		self.mark = entry 
		#exit price
		self.exit = exit 
		self.order_id = order_id 

	def __get_value(self):
		return (self.mark - self.entry) * self.size

	value = property(__get_value)

	def __set_entry(self, x):
		if not x is None and not isinstance(x, decimal.Decimal):
			self._entry = D(str(x))
		else:
			self._entry = x
	def __get_entry(self):
		return self._entry
	entry = property(__get_entry, __set_entry)

	def __set_mark(self, x):
		if not x is None and not isinstance(x, decimal.Decimal):
			self._mark = D(str(x))
		else:
			self._mark = x
	def __get_mark(self):
		return self._mark
	mark = property(__get_mark, __set_mark)
	
	def __set_size(self, x):
		if not x is None and not isinstance(x, decimal.Decimal):
			self._size = D(str(x))
		else:
			self._size = x
	def __get_size(self):
		return self._size
	size = property(__get_size, __set_size)

	def __set_exit(self, x):
		if not x is None and not isinstance(x, decimal.Decimal):
			self._exit = D(str(x))
		else:
			self._exit = x
	def __get_exit(self):
		return self._exit
	exit = property(__get_exit, __set_exit)

	def __get_closed(self):
		return not self.exit is None
	closed = property(__get_closed)

	def __str__(self):
		if self.entry is None or self.mark is None or self.size is None:
			s = "%s,%s,%s,%d,%s" % (self.symbol, str(self.entry), str(self.exit), self.nbars, "<no value set>")
		else:
			s = "%s,%s,%s,%d,%.2f" % (self.symbol, str(self.entry), str(self.exit), self.nbars, self.value)
		return(s)

class PositionList(object):

	#position closed callback
	def cb_noop(self, p):
		pass

	def __init__(self, close_cb=None):
		self.open = []
		self.closed = []
		self.rewinded = []
		if close_cb is None:
			self.close_cb = self.cb_noop
		else:
			self.close_cb = close_cb	

	def mark(self, bar):

		for p in self.open:
			if p.symbol != bar.symbol:
				continue
			p.mark = bar.cl
			p.nbars += 1

	def __find_pos(self, order_id):
		for p in self.open:
			if p.order_id == order_id:
				return(p)

		#for p in self.rewinded:
		#	if p.order_id == order_id:
		#		return(p)
		return None

	def rewind(self, order_id):

		for p in self.open[:]:
			if p.order_id == order_id:
				self.open.remove(p)
				self.rewinded.append(p)
				#print 'PositionList rewinded %s' % p.order_id
				return p
		return None
				
	#take an order and make it a position
	#i.e. an order from the orderbook has been filled
	def add(self, order, dt, level=None):

		#print "open orders\n"
		#print [p.order_id for p in self.open]

		#see if order was triggered by some other order
		#eg order o1 might trigger o2 when it is filled, i.e a o1 is a limit buy has contingent stop o2
		#that only becomes active once o1 is actually filled.
		#if that is the case o2.triggered() will be true here, which means we should find o1 and close it
		#rather than treating o2 as a new position to open. 
		#likewise if a linked order o2 is filled, it means to close the order that o2.link points to 

		if order.triggered() or order.link != None:

			## xxx would be best to decouple PosList from OB ... 

			#this is a bit messy. triggers behave differently in they are
			#added to the order book as state PENDING, whereas linked orders
			#we want to become active straight away.
			#this complexity could go away if we could open/close based on size
			#and partial closes here

			if order.triggered():
				clsid = order.trigger_parent
			else:
				clsid = order.link

			p = self.__find_pos(clsid)
			if p is None:
				raise Exception("cannot find parent to close, this id %d, parent %d" % (order.id, order.trigger_parent, clsid))

			#todo is to make it so we can close partial orders
			#we could split the current position into 2
			# both have the same entry level
			# one has size = p.size - order.size and stays open, mark = order.level
			# the other has size = order.size and is closed
			# but i dont actually need that right now
			if p.size + order.size != 0:
				raise Exception("order size mismatch id %d size %.1f to close orig id %d size %.1f" % (order.id, order.size, p.id, p.size))

			#order.level might be None if we have a MARKET order filled
			#in which case level should be passed here

			if order.level != None:
				final_level = order.level
			#elif not level is None:
			#	final_level = level
			else:
				raise InvalidLevelException("No level to close order at order id [%d] to close id [%d]" % (clsid, p.order_id))
			
			#mark it at the close levels
			p.mark = final_level
			p.exit = final_level	
			#take it off the open
			self.open.remove(p)
			self.closed.append(p)
			#call the position closed call back
			self.close_cb(p)

			#print "entry %.4f mark %.4f net %.4f size %.1f" % (p.entry, p.mark, p.mark - p.entry, p.size)
			#print "closed val: %.2f" % p.value
			#print "closed order for order id %d" % clsid 
		else:
			#add a new pos
			if not level is None:
				entry_level = level
			else:
				entry_level = order.level
			p = Position(symbol=order.symbol, dt=dt, entry=entry_level, size=order.size, order_id=order.id)
			self.open.append(p)
			#print "added pos for order id %d" % order.id
			#print [x.order_id for x in self.open]
		return p 
			
	def close_all(self, mark_level=None):
	
		for p in self.open[:]:
			self.close(p, mark_level)

	def close(self, p, mark_level=None):
		
		#position mark should be up to date
		if mark_level is None:
			m = p.mark
		else:
			m = mark_level

		p.exit = m
		self.open.remove(p)
		self.closed.append(p)
		self.close_cb(p)

	def net_size(self):
		sum = 0
		for p in self.open:
			sum += p.size
		return sum

	def value(self):
		val = 0
		for p in self.open:
			val += p.value
		return val	

	def sym_open(self, sym):
		return [p for p in self.open if p.symbol == sym]
		
class BackTest(object):

	def __init__(self, equity=100000):
		deq = D(str(equity))
		self.equity = deq #equity
		self.max_equity = self.min_equity = deq #equity
		self.max_risk = 0.01
		self.eqvals = []
		self.bars = {} 
		self.inputs = []
		self.book = OrderBook(debug=False)
		self.poslist = PositionList(close_cb=self.close_cb)
		

	def __get_max_equity(self):
		return self._max_equity
	def __set_max_equity(self, x):
		if not isinstance(x, decimal.Decimal):
			self._max_equity = D(str(x))
		else:
			self._max_equity = x
	max_equity = property(__get_max_equity, __set_max_equity)

	def __get_min_equity(self):
		return self._min_equity
	def __set_min_equity(self, x):
		if not isinstance(x, decimal.Decimal):
			self._min_equity = D(str(x))
		else:
			self._min_equity = x
	min_equity = property(__get_min_equity, __set_min_equity)

	def __get_equity(self):
		return self._equity
	def __set_equity(self, x):
		if not isinstance(x, decimal.Decimal):
			self._equity = D(str(x))
		else:
			self._equity = x
	equity = property(__get_equity, __set_equity)

	def __get_max_risk(self):
		return self._max_risk
	def __set_max_risk(self, x):
		if not isinstance(x, decimal.Decimal):
			self._max_risk = D(str(x))
		else:
			self._max_risk = x
	max_risk = property(__get_max_risk, __set_max_risk)

	#override this
	def on_close(self, p):
		pass

	### callback for when a position is closed
	def close_cb(self, p):

		self.on_close(p)

		self.equity += p.value
		if self.equity > self.max_equity:
			self.max_equity = self.equity
		elif self.equity < self.min_equity:
			self.min_equity = self.equity

		#print "BackTest close callback() pos: %.2f, equity %.2f" % (p.value, self.equity)

	###
	# add an input source from which to read bar data	
	# pass the string symbol, input object that supports readline()
	# and an optional bar type for parsing the input 
	def add_input(self, sym, inf, bartype=Bar):

		#print 'adding sym %s' % sym
		self.inputs.append((sym, inf, bartype))
		self.bars[sym] = []

	###
	# update the current equity level
	# if you don't want this done every bar, override it and check the bar date
	# e.g. tracking end of day equity for an hourly strategy, hourly bars, daily equity
	def update_eqvals(self, b):
		self.eqvals.append((b.date, self.equity + self.poslist.value()))

	#run the strat, you set the input by calling add_input() before 
	def run(self):

		# ugh ... clean this up
		done = False
		while done == False:
			for (sym, f, bartype) in self.inputs:
				#print "Sym: %s" % sym
				line = f.readline().strip()
				#print 'line: %s' % line
				if len(line) == 0:
					done = True
					break
				b = bartype(sym, line)
				self.next_bar(sym, b)
			self.update_eqvals(b)
	
	### 
	# this is a mostly internal function
	# it will handle fills and marking open positions
	# as well as the list of past bars
	def next_bar(self, sym, b):

		#skip weekends
		if b.date.weekday() == 5 or b.date.weekday() == 6:
			return

		#first check if this bar caused any orders to be filled
		fills = self.book.get_fills(b)
		
		if len(fills) > 1:
			# we got multiple fills
			#print "Multiple fills:"
			for order in fills[:]:
				#see if any of the other fills are meant to cancel this order
				dups = [x for x in fills if order.id in x.cancels]
				if len(dups) == 0:
					continue
				#we have 2 orders triggered that would cancel each other
				# could be they are stops/tp for a parent, in which case
				# close the parent and cancel these two
				if order.triggered:
					self.poslist.rewind(order.trigger_parent)
				# cancel the conflicting orders ...
				self.book.cancel(order)
				fills.remove(order)
				for d in dups:
					#print "DUP cancel %s %s" % (order, d)
					self.book.cancel(d)
					fills.remove(d)

		#we cleared out any dupes, now fill them
		for o in fills: 
			#print "\nOrder to be filled:\n%s\n%s\n" % (o, b)

			#add the order to the position mgr for this symbol
			self.poslist.add(o, b.date)
			#update the order book
			self.book.fill(o)

		self.poslist.mark(b)

		#print "%d active %d cancelled %d filled" % (len(book.active), len(book.cancelled), len(book.filled))
		#print "%d open positions %d closed" % (len(self.poslist.open), len(self.poslist.closed))
		
		if not self.bars.has_key(sym):
			self.bars[sym] = []
	
		#if len(self.bars[sym]) == 0:
		#	self.bars[sym].append(b)
		#	return

		#pass it to the strat
		self.bar_close(sym, b)
		
		self.bars[sym].append(b)


	###
	# this is the main function to override when doing ur strat
	###
	def bar_close(self, sym, b):

		pass

	def print_summary(self):

		nwin = 0
		nlos = 0
		totwin = 0
		totlos = 0
		for p in self.poslist.closed:
			if p.value >= 0:
				nwin += 1
				totwin += p.value
			else:
				nlos += 1
				totlos += p.value

		tot_pos = D(nwin + nlos)
		print "%d won %d los" % (nwin, nlos)
		if nwin == 0 or nlos == 0:
			print "final equity: %.2f max %.2f min %.2f" % (self.equity, self.max_equity, 
				self.min_equity)
			return
		pos_won = nwin/tot_pos
		pos_los = nlos/tot_pos 
		print "%d won %d los win rate %.2f" % (nwin, nlos, pos_won)
		avg_win = totwin/nwin
		avg_los = totlos/nlos
		print "avg win %.2f avg los %.2f" % (avg_win, avg_los)
		print "wl_rat %.2f" % (avg_win/abs(avg_los)),
		print "e %.2f" % (avg_win * pos_won + avg_los * pos_los)
		print "final equity: %.2f max %.2f min %.2f" % (self.equity, self.max_equity, 
			self.min_equity)

	def unq_name(self, outfile_base, outfile_ext):
		i = 1
		while True:
			outfile = "%s-%02d.%s" % (outfile_base, i, outfile_ext)
			try:
				os.stat(outfile)
			except OSError:
				break
			i += 1
		return outfile

	def write_eqvals(self, outfile):
		w = csv.writer(open(outfile, 'wb'))
		for x in self.eqvals:
			w.writerow(x)

	### 
	# write date, equity tuples to csv file
	#
	def write_eqvals_unq(self, outfile_base, outfile_ext='csv'):
		
		self.write_eqvals(self.unq_name(outfile_base, outfile_ext))
	

