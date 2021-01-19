def math(mathstr):
	while True:
		lbrackets = []
		for i, mathchar in enumerate(mathstr):
			if mathchar == '(':
				lbrackets.append(i)
			elif mathchar == ')':
				if len(lbrackets) == 1:
					bstart = lbrackets.pop()
					bend = i
					break
				elif len(lbrackets) > 0:
					lbrackets.pop()
		else:
			break
		mathstr = mathstr[0:bstart] + math(mathstr[bstart+1:bend]) + mathstr[bend+1:]
	opdicts = {
		'+': (lambda a, b: a + b),
		'-': (lambda a, b: a - b),
		'*': (lambda a, b: a * b),
		'/': (lambda a, b: a / b),
		'%': (lambda a, b: a % b),
		'^': (lambda a, b: a ** b),
		'**': (lambda a, b: a ** b),
	}
	for opstr, opfunc in opdicts.items():
		op_index = mathstr.find(opstr)
		if op_index != -1:
			try:
				mathstr = str(opfunc(float(math(mathstr[:op_index])), float(math(mathstr[op_index+1:]))))
			except ValueError:
				pass
			except ZeroDivisionError:
				mathstr = 'Zero Division Error'
			except OverflowError:
				mathstr = 'Overflow Error'
	return mathstr

mathstr = '((10 + (5 * 2)) + (7 / 5))'
print(math(mathstr))
