import qt
import msvcrt

sspd = qt.instruments['snspd']
v0 = 5 #volt
sspd.set_bias0(v0)
v1 = 5 #volt
sspd.set_bias1(v1)

qt.mstart()
while 1:

    if (msvcrt.kbhit() and (msvcrt.getch() == 'q')): break
    counts = sspd.get_counts()
    sspd.check()
    qt.msleep(0.5)

qt.mend()