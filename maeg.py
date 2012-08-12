from backtest import *

class MABackTest(BackTest):

	
	def bar_close(self, sym, b):

		ma = 200 
		if (len(self.bars[sym]) < ma):
			return

		# if price is above the ma, we want to be long
		# if price is below the ma, we want to be out

		#calculate the ma
		close_ma = sum([x.cl for x in self.bars[sym][-ma:]])/ma

		if b.cl > close_ma: #price is above ma, so make sure we are long
			if len(self.poslist.sym_open(sym)) == 0: #no open orders
				base_size = self.equity / b.cl # how many shares we could buy	
				odd_lot = base_size % 100 
				trade_size = base_size - odd_lot #round to 00's 
				if trade_size < 100:
					print "trade_size %d, equity %.2f" % (trade_size, self.equity)
					return	
				o = Order(sym, Order.BUY, Order.MARKET, level=b.cl, size=trade_size)
				print '\nCrossed over, adding long'
				print "%s" % o
				self.book.add(o)
		else: #gone under ma, get out
			for pos in self.poslist.sym_open(sym):
				cls_order = Order(sym, Order.SELL, Order.MARKET, level=b.cl, size=-pos.size, link=pos.order_id)
				print "Gone under ma ... closing pos for order id %d" % pos.order_id
				print "%s" % cls_order
				self.book.add(cls_order)	


		return
				

if __name__ == '__main__':

	if len(sys.argv) < 2:
		print "usage: %s <input file>" % (sys.argv[0])
		sys.exit(1)

	bt = MABackTest()

	for i in xrange(1, len(sys.argv)):
		fname = sys.argv[i]
		sym = fname.split('_')[-1]
		idx = sym.find('.')
		if idx != -1:
			sym = sym[0:idx]	
		f = open(fname)
		l = f.readline()
		if l.find('Open,') == -1: #no header
			f.seek(0)
			t = Bar
		else:
			t = YahooBar
		bt.add_input(sym, f, t)

	bt.run()

	print "%d open %d closed %d rewound" % (len(bt.poslist.open), len(bt.poslist.closed), len(bt.poslist.rewinded))
	bt.poslist.close_all()

	bt.print_summary()
	
	#for p in bt.poslist.closed:
	#	print "%s" % p

