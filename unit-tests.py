import unittest
from backtest import Bar
from backtest import Order
from backtest import OrderBook
from backtest import Position
from backtest import PositionList
from backtest import BackTest
from backtest import InvalidOrderException, InvalidStateException
from datetime import datetime

class TestBarFunctions(unittest.TestCase):

	raw_data = """20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506
20010103-000000,EURUSD,0.9506,0.9510,0.9492,0.9496
20010103-010000,EURUSD,0.9496,0.9509,0.9495,0.9505
20010103-020000,EURUSD,0.9504,0.9508,0.9498,0.9499
20010103-030000,EURUSD,0.9499,0.9507,0.9499,0.9503"""
	def setUp(self):
		self.sym = "ABC"
		self.data = [];

		for l in self.raw_data.split('\n'):
			self.data.append(l)


	def test_init(self):
		b = Bar(self.sym, self.data[0])

	def test_merge_bar(self):
		bc = Bar(self.sym, self.data[0])

		b1 = Bar(self.sym, self.data[0])
		b2 = Bar(self.sym, self.data[1])

		#base case b2 should replace all of b1 except open and date
		b1.merge(b2)
		self.assertTrue(b1.date == bc.date)
		self.assertTrue(b1.op == bc.op)
		self.assertTrue(b1.hi == b2.hi)
		self.assertTrue(b1.lo == b2.lo)
		self.assertTrue(b1.cl == b2.cl)

	def test_merge_direct(self):
		
		bc = Bar(self.sym, self.data[0])

		b1 = Bar(self.sym, self.data[0])
		b2 = Bar(self.sym, self.data[1])
			
		b1.merge(b2.cl, b2.hi, b2.lo)
		self.assertTrue(b1.date == bc.date)
		self.assertTrue(b1.op == bc.op)
		self.assertTrue(b1.hi == b2.hi)
		self.assertTrue(b1.lo == b2.lo)
		self.assertTrue(b1.cl == b2.cl)
		
		b1 = Bar(self.sym, self.data[0])
		b1.merge(b2.cl, b2.hi)
		self.assertTrue(b1.date == bc.date)
		self.assertTrue(b1.op == bc.op)
		self.assertTrue(b1.hi == b2.hi)
		self.assertTrue(b1.lo == bc.lo)
		self.assertTrue(b1.cl == b2.cl)
	
		b1 = Bar(self.sym, self.data[0])
		b1.merge(b2.cl)
		self.assertTrue(b1.date == bc.date)
		self.assertTrue(b1.op == bc.op)
		self.assertTrue(b1.hi == bc.hi)
		self.assertTrue(b1.lo == bc.lo)
		self.assertTrue(b1.cl == b2.cl)

class TestOrderObject(unittest.TestCase):

	def setUp(self):
		self.sym = "AAPL"
		#yup
		self.aEq = self.assertEqual
		self.aIn = self.assertIn
		self.aRaise = self.assertRaises

	def tearDown(self):
		pass

	def test_init(self):

		o = Order()
		#default order state
		self.aEq(o.state, Order.UNSUB)
		#no cancels, no triggers
		self.aEq(len(o.cancels), 0)
		self.aEq(len(o.triggers), 0)

	def test_cancels(self):

		o1 = Order()
		o2 = Order()
		o1.cancel(o2)

		#o2 should be in list of orders cancelled if o1 is filled
		self.aEq(len(o1.cancels), 1)	
		self.aIn(o2.id, o1.cancels)
		#o2's cancel parent should be o1
		self.aEq(o2.cancel_parent, o1.id)

	def test_cancels_iter(self):

		o1 = Order()
		o2 = Order()
		o3 = Order()
		o1.cancel((o2, o3))

		#o2 & o3 should be in list of orders cancelled if o1 is filled
		self.aEq(len(o1.cancels), 2)	
		self.aIn(o2.id, o1.cancels)
		self.aIn(o3.id, o1.cancels)
		#o2's cancel parent should be o1
		self.aEq(o2.cancel_parent, o1.id)
		#o3's cancel parent should be o1
		self.aEq(o3.cancel_parent, o1.id)

	def test_cancels_none(self):

		o1 = Order(self.sym, Order.BUY, Order.LIMIT, level=550, size=100)
		self.aRaise(InvalidOrderException, o1.cancel, None) 

	def test_oco(self):
		o1 = Order()
		o2 = Order()
		Order.OCO(o1, o2)
		self.aEq(len(o1.cancels), 1)
		self.aIn(o2.id, o1.cancels)
		self.aEq(o2.cancel_parent, o1.id)
		self.aEq(len(o2.cancels), 1)
		self.aIn(o1.id, o2.cancels)
		self.aEq(o1.cancel_parent, o2.id)

		with self.aRaise(InvalidOrderException):
			Order.OCO(o1, None)
		with self.aRaise(InvalidOrderException):
			Order.OCO(o1, (o2,))
		with self.aRaise(TypeError):
			Order.OCO((o1,), o2)

	def test_state(self):

		o1 = Order() 
		for state in Order.StateList:
			o1.state = state 
			self.aEq(o1.state, state)	
		with self.aRaise(InvalidStateException):
			o1.state = -1

	def test_size(self):
		o1 = Order()
		with self.aRaise(InvalidOrderException):
			o1.size = 100
		o1 = Order(dir=Order.BUY, size=100)
		self.aEq(o1.size, 100)
		
		#buy orders can only be 0 or positive
		with self.aRaise(InvalidOrderException):
			o1.size = -100
		
		#sell orders can only be 0 or negative
		o1.dir = Order.SELL
		o1.size = -100
		self.aEq(o1.size, -100)
		with self.aRaise(InvalidOrderException):
			o1.size = 100
	
	def test_trigger(self):
		o1 = Order()
		o2 = Order()

		o1.trigger(o2)	
		self.aEq(len(o1.triggers), 1)
		self.aIn(o2.id, o1.triggers)
		self.aEq(o2.trigger_parent, o1.id)
		self.aEq(o2.triggered(), True)

	def test_trigger_iter(self):

		o1 = Order()
		o2 = Order()
		o3 = Order()

		o1.trigger(o2, o3)
		self.aEq(len(o1.triggers), 2)
		self.aIn(o2.id, o1.triggers)
		self.aIn(o3.id, o1.triggers)
		self.aEq(o2.trigger_parent, o1.id)
		self.aEq(o2.triggered(), True)
		self.aEq(o3.trigger_parent, o1.id)
		self.aEq(o3.triggered(), True)

	def test_validate(self):

		#no order type set
		o1 = Order(dir=Order.BUY, size=100, level=100) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 100)

		#no level set
		o1 = Order(dir=Order.BUY, size=100, type=Order.LIMIT) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 100)

		#a buy limit must be lower than the mark
		o1 = Order(dir=Order.BUY, size=100, type=Order.LIMIT, level=100) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 99)
		
		#should not raise anything
		Order.validate(o1, 101)
		
		#a buy stop must be higher than the mark
		o1 = Order(dir=Order.BUY, size=100, type=Order.STOP, level=100) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 101)
		
		#should not raise anything
		Order.validate(o1, 99)
	
		#a sell limit must be higher than mark
		o1 = Order(dir=Order.SELL, size=-100, type=Order.LIMIT, level=100) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 101)

		#should not raise anything
		Order.validate(o1, 99)

		#a sell stop must be lower than mark
		o1 = Order(dir=Order.SELL, size=-100, type=Order.STOP, level=100) 
		self.aRaise(InvalidOrderException, Order.validate, o1, 99)
		
		#should not raise anything 
		Order.validate(o1, 101)


class TestOrderBookObject(unittest.TestCase):

	def setUp(self):
		self.sym = "EURUSD"
		self.aEq = self.assertEqual
		self.aIn = self.assertIn
		self.aItEq = self.assertItemsEqual
		self.aRaise = self.assertRaises
		self.debug = False
		#self.ob = OrderBook(debug=True)	
		self.ob = OrderBook(self.debug)	

	def tearDown(self):
		#self.ob = OrderBook(self.debug)	
		pass

	def testAddSingle(self):

		o1 = Order()
		self.ob.add(o1)

		#adding an order should add it to the active queue of the book
		self.aEq(len(self.ob.active), 1)
		self.aIn(o1.id, self.ob.active)
		#and set its state to active
		self.aEq(o1.state, Order.ACTIVE)	

		#test single dup
		self.aRaise(InvalidOrderException, self.ob.add, o1)

	def testAddIter(self):

		tl = (Order(), Order(), Order())
		self.ob.add(tl)
		self.aItEq([x.id for x in tl], self.ob.active)
		for o in tl:
			self.aEq(o.state, Order.ACTIVE)

		#test dupes are detected
		self.aRaise(InvalidOrderException, self.ob.add, tl[0])
		self.aRaise(InvalidOrderException, self.ob.add, tl)

	def testAddMult(self):
		o1 = Order()
		o2 = Order()
		o3 = Order()
		self.ob.add(o1, o2, o3)

		self.aItEq([o1.id, o2.id, o3.id], self.ob.active)
		for o in (o1, o2, o3):
			self.aEq(o.state, Order.ACTIVE)

		self.aRaise(InvalidOrderException, self.ob.add, o1, o2, o3)

	def testAddPending(self):

		o1 = Order()
		o2 = Order()
		#must still add o2
		o1.trigger(o2)

		#triggered orders should be set to pending an added to pending queue
		self.ob.add(o1, o2)
		self.aEq(o1.state, Order.ACTIVE)
		self.aEq(o2.state, Order.PENDING)
		self.aIn(o2.id, self.ob.pending)
	
	def testCancel(self):

		o1 = Order()
		o2 = Order()

		self.ob.add(o1, o2)
		
		self.ob.cancel(o1)
		#cancel by id
		self.ob.cancel(o2.id)

		self.aEq(o1.state, Order.CANCELLED)
		self.aEq(o2.state, Order.CANCELLED)
		self.aItEq([o1.id, o2.id], self.ob.cancelled)
		
		#cancel a non existent order returns false
		self.aEq(self.ob.cancel(None), False)
		self.aEq(self.ob.cancel(-1), False)

	def testCancelTriggers(self):
		o1 = Order()
		o2 = Order()
		o3 = Order()

		o1.trigger(o2)
		o2.trigger(o3)
		self.ob.add(o1, o2, o3)

		#cancel o1 should cancel o2 as well and add both to the cancelled queue
		self.aEq(self.ob.cancel(o1), True)
		self.aEq(o1.state, Order.CANCELLED)
		self.aEq(o2.state, Order.CANCELLED)
		self.aEq(o3.state, Order.CANCELLED)
		self.aItEq([o1.id, o2.id, o3.id], self.ob.cancelled)
		
	def testCancelAll(self):

		o1 = Order()
		o2 = Order()
		o3 = Order()
		o4 = Order()

		o1.trigger(o2)		
		o1.trigger(o3)

		self.ob.add(o1, o2, o3, o4)
		
		self.ob.cancel_all()

		self.aItEq([o1.id, o2.id, o3.id, o4.id], self.ob.cancelled)

	def testFill(self):
		
		o1 = Order()
		self.ob.add(o1)

		self.aEq(self.ob.fill(o1), True)
		self.aEq(o1.state, Order.FILLED)
		self.aEq([o1.id], self.ob.filled)
		
		self.aEq(self.ob.fill(None), False)
		self.aEq(self.ob.fill(o1), False)

	def testFillTrigger(self):

		o1 = Order()
		o2 = Order()
		
		o1.trigger(o2)
		self.ob.add(o1, o2)

		self.aEq(o2.state, Order.PENDING)
		self.aEq(self.ob.fill(o1), True)	
		self.aEq(o2.state, Order.ACTIVE)
		self.aEq([o2.id], self.ob.active)

	def testFillCancel(self):

		o1 = Order()
		o2 = Order()
		
		o1.cancel(o2)
		self.ob.add(o1, o2)

		self.aEq(self.ob.fill(o1), True)	
		self.aEq(o2.state, Order.CANCELLED)
		self.aEq([o2.id], self.ob.cancelled)

	def testGetFills(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.LIMIT, level=0.9551, size=1) 
		o2 = Order(symbol="NOPE", dir=Order.BUY, type=Order.LIMIT, level=0.9551, size=1) 
		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9560,0.9505,0.9506")

		self.ob.add(o1)
		self.ob.add(o2)
		self.aEq([], self.ob.get_fills(b1))
		self.aEq([o1], self.ob.get_fills(b2))

		#market orders always get filled the next bar
		#the "fill price" is really just the level set on the order ... 
		o3 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9551, size=1) 
		self.ob.add(o3)
		self.aEq([o3], self.ob.get_fills(b1))

class TestPosition(unittest.TestCase):

	def setUp(self):
		self.sym = "EURUSD"
		self.aEq = self.assertEqual
		self.aIn = self.assertIn
		self.aT = self.assertTrue
		self.aRaise = self.assertRaises

	def tearDown(self):
		pass

	def testValueLong(self):
	
		p = Position(self.sym, entry=1.0000, size=10000)
		self.aEq(p.value, 0) 

		p.mark = 1.0001
		self.aEq(p.value, 1)

		p.mark = 0.9999
		self.aEq(p.value, -1)

	def testValueShort(self):
		p = Position(self.sym, entry=1.0000, size=-10000)
		self.aEq(p.value, 0)
	
		p.mark = 1.0001
		self.aEq(p.value, -1)
	
		p.mark = 0.9999
		self.aEq(p.value, 1)

	def testToStr(self):

		#this is more about checking __str__ works with empty vals than testing str()
		p = Position()
		self.aT(isinstance(str(p), str))

		p = Position(self.sym, entry=1.0000, size=10000, exit=1.0001)
		self.aT(isinstance(str(p), str))
 
class TestPositionList(unittest.TestCase):

	def setUp(self):
		self.sym = "EURUSD"
		self.aEq = self.assertEqual
		self.aIn = self.assertIn
		self.aRaise = self.assertRaises
		self.pl = PositionList() 
		#self.ob = OrderBook(debug=False)

	def tearDown(self):
		pass

	def testAddEmpty(self):
		o = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		p = self.pl.add(o, datetime.now())
		self.aEq(self.pl.open, [p])
		self.aEq(p.order_id, o.id)
			
	def testAddEmptyLevel(self):
		o = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		p = self.pl.add(o, datetime.now(), level=2.0)
		self.aEq(p.entry, 2.0)
		self.aEq(p.mark, 2.0)
		self.aEq(self.pl.open, [p])
	
	def testAddTriggered(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=1.1000, size=-10000) 
		o1.trigger(o2)
		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o2, datetime.now())
		
		self.aEq([p1], self.pl.closed)
		self.aEq([], self.pl.open)
		

	def testAddLink(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=1.1000, size=-10000, link=o1.id) 
		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o2, datetime.now())
		
		self.aEq([p1], self.pl.closed)
		self.aEq([], self.pl.open)

	def testMark(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order("NOPE", dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		
		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o1, datetime.now())
		p3 = self.pl.add(o2, datetime.now())

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		
		self.pl.mark(b1)

		#mark should update p1 & p2 but not p3
		self.aEq(p1.mark, b1.cl)
		self.aEq(p2.mark, b1.cl)
		self.aEq(p3.mark, o2.level)

	def testRewind(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.rewind(o1.id)
		self.aEq(p1, p2)

		self.aEq([], self.pl.open)
		self.aEq([p1], self.pl.rewinded)

	def testClose(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		p1 = self.pl.add(o1, datetime.now())

		self.pl.close(p1)
		self.aEq([], self.pl.open)
		self.aEq([p1], self.pl.closed)
		self.aEq(p1.exit, o1.level)
		self.aEq(p1.exit, p1.mark)

	def testCloseMark(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		p1 = self.pl.add(o1, datetime.now())
	
		#close @ a specified mark level	
		self.pl.close(p1, mark_level=2.0)
		self.aEq([], self.pl.open)
		self.aEq([p1], self.pl.closed)
		self.aEq(p1.exit, 2.0)
	
	def testCloseAll(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o3 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o4 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 

		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o2, datetime.now())
		p3 = self.pl.add(o2, datetime.now())
		p4 = self.pl.add(o2, datetime.now())

		self.pl.close_all()

		self.aEq([], self.pl.open)
		self.aEq([p1, p2, p3, p4], self.pl.closed)
			

	def testNetSize(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=100) 
		o2 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=1000) 
		o3 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
	
		for o in (o1, o2, o3):
			self.pl.add(o, datetime.now())

		self.aEq(self.pl.net_size(), 11100)	
			
	def testValue(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order(self.sym, dir=Order.SELL, type=Order.MARKET, level=1.0000, size=-10000) 

		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o2, datetime.now())
	
		#mark = entry
		self.aEq(self.pl.value(), 0)

		p1.mark = 1.0001
		self.aEq(self.pl.value(), 1)

		p2.mark = 0.9998
		self.aEq(self.pl.value(), 3)

		p1.mark = 0.9999
		self.aEq(self.pl.value(), 1)

		p2.mark = 1.0001
		self.aEq(self.pl.value(), -2)

	def testSymOpen(self):

		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o2 = Order("NOPE", dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 
		o3 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=1.0000, size=10000) 

		p1 = self.pl.add(o1, datetime.now())
		p2 = self.pl.add(o2, datetime.now())
		p3 = self.pl.add(o3, datetime.now())

		self.aEq(self.pl.sym_open(self.sym), [p1, p3])
		self.aEq(self.pl.sym_open("NOPE"), [p2])
		self.aEq(self.pl.sym_open("PETE"), [])
		self.aEq(self.pl.sym_open(None), [])

class TestBackTest(unittest.TestCase):

	def setUp(self):
		self.sym = "EURUSD"
		self.aEq = self.assertEqual
		self.aIn = self.assertIn
		self.aRaise = self.assertRaises
		self.aItEq = self.assertItemsEqual
		self.bt = BackTest()

	def tearDown(self):
		pass

	def bar_close(self, sym, b):
		print "bar_close: ", b.date

	def testAddSym(self):
		
		f = "yo" 
		self.bt.add_input(self.sym, f, bartype=Bar)
		self.aEq([(self.sym, f, Bar)], self.bt.inputs)
		self.aEq(self.bt.bars.keys(), [self.sym])

	def testBuyMarket(self):

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9508, size=10000) 
		self.bt.book.add(o1)
	
		#self.bt.bar_close = self.bar_close

		self.bt.next_bar(self.sym, b1)
		
		#should have an open position
		self.aEq(len(self.bt.poslist.open), 1)
		p = self.bt.poslist.open[0]
		self.aEq(p.order_id, o1.id)
		self.aEq(p.mark, b1.cl)
		self.aEq(p.entry, o1.level)

	def testBuyLimit(self):

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9500,0.9506")
		o1 = Order(self.sym, dir=Order.BUY, type=Order.LIMIT, level=0.9501, size=10000) 
		self.bt.book.add(o1)
	
		self.bt.next_bar(self.sym, b1)
		
		#should be no fill for b1 
		self.aEq(len(self.bt.poslist.open), 0)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 1)

	def testBuyStop(self):

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9511,0.9500,0.9506")
		o1 = Order(self.sym, dir=Order.BUY, type=Order.STOP, level=0.9510, size=10000) 
		self.bt.book.add(o1)
	
		self.bt.next_bar(self.sym, b1)
		self.aEq(len(self.bt.poslist.open), 0)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 1)

	def testSellLimit(self):

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9511,0.9505,0.9506")
		o1 = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=0.9510, size=-10000) 
		self.bt.book.add(o1)
	
		self.bt.next_bar(self.sym, b1)
		self.aEq(len(self.bt.poslist.open), 0)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 1)

	def testSellStop(self):

		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9499,0.9506")
		o1 = Order(self.sym, dir=Order.SELL, type=Order.STOP, level=0.9499, size=-10000) 
		self.bt.book.add(o1)
	
		self.bt.next_bar(self.sym, b1)
		self.aEq(len(self.bt.poslist.open), 0)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 1)

	def testTP(self):
		
		#stop loss/take profit
		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9511,0.9505,0.9506")
		#buy order at 9505
		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9505, size=10000) 
		#stop loss at 9499
		sl = Order(self.sym, dir=Order.SELL, type=Order.STOP, level=0.9499, size=-10000) 
		#take profit at 9510
		tp = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=0.9510, size=-10000) 

		#stop loss hit cancels tp and vice versa
		Order.OCO(sl, tp)
		#when the order is filled it activates sl/tp			
		o1.trigger(sl, tp)

		self.bt.book.add(o1, sl, tp)

		self.bt.next_bar(self.sym, b1)
		#the order should be filled
		self.aEq(len(self.bt.poslist.open), 1)
		self.aItEq([sl.id, tp.id], self.bt.book.active)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 0)
		self.aEq(len(self.bt.poslist.closed), 1)
		self.aEq(len(self.bt.book.active), 0)

		self.aEq(self.bt.equity, 100005)

	def testSL(self):
		
		#stop loss/take profit
		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9499,0.9506")
		#buy order at 9505
		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9505, size=10000) 
		#stop loss at 9499
		sl = Order(self.sym, dir=Order.SELL, type=Order.STOP, level=0.9499, size=-10000) 
		#take profit at 9510
		tp = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=0.9510, size=-10000) 

		#stop loss hit cancels tp and vice versa
		Order.OCO(sl, tp)
		#when the order is filled it activates sl/tp			
		o1.trigger(sl, tp)

		self.bt.book.add(o1, sl, tp)

		self.bt.next_bar(self.sym, b1)
		#the order should be filled
		self.aEq(len(self.bt.poslist.open), 1)
		self.aItEq([sl.id, tp.id], self.bt.book.active)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 0)
		self.aEq(len(self.bt.poslist.closed), 1)
		self.aEq(len(self.bt.book.active), 0)

		self.aEq(self.bt.equity, 99994) 

	def testRewind(self):
		
		#in this case we have a sl/tp, and get a bar which triggers them both
		#when this happens, we cancel both the orders and unwind the original position
		#as if it never happened. If this is happening a lot you need lower time frame data

		#stop loss/take profit
		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9509,0.9505,0.9506")
		b2 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9510,0.9499,0.9506")
		#buy order at 9505
		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9505, size=10000) 
		#stop loss at 9499
		sl = Order(self.sym, dir=Order.SELL, type=Order.STOP, level=0.9499, size=-10000) 
		#take profit at 9510
		tp = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=0.9510, size=-10000) 

		#stop loss hit cancels tp and vice versa
		Order.OCO(sl, tp)
		#when the order is filled it activates sl/tp			
		o1.trigger(sl, tp)

		self.bt.book.add(o1, sl, tp)

		self.bt.next_bar(self.sym, b1)
		#the order should be filled
		self.aEq(len(self.bt.poslist.open), 1)
		self.aItEq([sl.id, tp.id], self.bt.book.active)

		self.bt.next_bar(self.sym, b2)
		self.aEq(len(self.bt.poslist.open), 0)
		self.aEq(len(self.bt.poslist.closed), 0)
		self.aEq(len(self.bt.poslist.rewinded), 1)
		self.aEq(len(self.bt.book.active), 0)

		self.aEq(self.bt.equity, 100000) 

	def testOpenRewind(self):
		
		#in this case we have a sl/tp, and get a bar which triggers them both
		#when this happens, we cancel both the orders and unwind the original position
		#as if it never happened. If this is happening a lot you need lower time frame data

		#stop loss/take profit
		b1 = Bar(self.sym, "20010102-230000,EURUSD,0.9507,0.9510,0.9499,0.9506")
		#buy order at 9505
		o1 = Order(self.sym, dir=Order.BUY, type=Order.MARKET, level=0.9505, size=10000) 
		#stop loss at 9499
		sl = Order(self.sym, dir=Order.SELL, type=Order.STOP, level=0.9499, size=-10000) 
		#take profit at 9510
		tp = Order(self.sym, dir=Order.SELL, type=Order.LIMIT, level=0.9510, size=-10000) 

		#stop loss hit cancels tp and vice versa
		Order.OCO(sl, tp)
		#when the order is filled it activates sl/tp			
		o1.trigger(sl, tp)

		self.bt.book.add(o1, sl, tp)

		self.bt.next_bar(self.sym, b1)
		#the order should be filled
		self.aEq(len(self.bt.poslist.open), 1)
		self.aItEq([sl.id, tp.id], self.bt.book.active)

		self.bt.next_bar(self.sym, b1)
		self.aEq(len(self.bt.poslist.open), 0)
		self.aEq(len(self.bt.poslist.closed), 0)
		self.aEq(len(self.bt.poslist.rewinded), 1)
		self.aEq(len(self.bt.book.active), 0)

		self.aEq(self.bt.equity, 100000) 


if __name__ == '__main__':
	unittest.main()
