import visa
import time

TL4001 = visa.instrument("USB0::0x1313::0x804A::M00277475::INSTR")
TL4001.write("*IDN?")
print TL4001.read()
TL4001.write("SYST:BEEP:IMM")
TL4001.write("CONF:TEMP")
TL4001.write("READ?")
print 'CONF:TEMP read is: %s' % TL4001.read()
#TL4001.write("INIT:IMM")
#TL4001.write("FETC:TEMP?")
#print TL4001.read()
#TL4001.write("FETC:POW?")
#print TL4001.read()

TL4001.write("SOUR:CURR:AMPL 0.642")
TL4001.write("SOUR:CURR:AMPL?")
print 'Source curr AMPL? read is: %s ' % TL4001.read()

TL4001.write("OUTP2:STATE 1")
TL4001.write("OUTP2:STATE")
print 'OUTP2 state is: %s ' % TL4001.read()
time.sleep(3)
TL4001.write("OUTP1:STATE 1")

time.sleep(3)
TL4001.write("OUTP2:STATE?")
print TL4001.read()
TL4001.write("OUTP1:STATE?")
print TL4001.read()


time.sleep(3)
TL4001.write("OUTP1:STATE 0")
time.sleep(2)
TL4001.write("OUTP2:STATE 0")
TL4001.write("OUTP2:STATE?")
print TL4001.read()
TL4001.write("OUTP1:STATE?")
print TL4001.read()