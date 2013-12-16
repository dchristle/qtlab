import qt

sspd = qt.instruments['SSPD1']
v0 = 5 #volt
sspd.set_bias0(v0)
v1 = 5 #volt
sspd.set_bias1(v1)

qt.mstart()
while True:
    counts = sspd.get_counts()
	sspd.check()
        
    qt.msleep(0.5)
    
qt.mend()