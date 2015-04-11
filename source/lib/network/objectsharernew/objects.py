# Some potentially useful shareable objects

class PythonInterpreter(object):

    def __init__(self, namespace={}):
        self._namespace = namespace

    def __str__(self):
        return 'A Python interpreter'

    def cmd(self, cmd, namespace=None):
        '''
        Execute a python command.
        Optionally use the namespace <namespace>, otherwise use the internally
        kept namespace.
        '''
        if namespace is None:
            namespace = self._namespace
        retval = eval(cmd, namespace, namespace)
        return retval

    def ip_queue(self, cmd):
        import code, threading, IPython
        c = code.compile_command(cmd)
        cev = threading.Event()
        rev = threading.Event()
        try:
            ip = IPython.core.ipapi.get()
        except:
            ip = IPython.ipapi.get()
        ip.IP.code_queue.put((c, cev, rev))

class EchoServer(object):

    def __init__(self):
        pass

    def echo(self, msg):
        return msg

