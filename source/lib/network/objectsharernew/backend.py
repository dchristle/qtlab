# backend.py, Reinier Heeres 2014
# Basic funcitons for objectsharer backends
import logging
import time
import types
import pickle
import traceback
import misc
import struct
import bisect


logger = None

class AsyncHelloReply(object):
    def __init__(self, target, backend):
        self.target = target
        self.target_uid = None
        self.backend = backend
        self.logged = 0

    def is_valid(self):
        uid = self.backend.get_uid_for_addr(self.target)
        if uid and self.logged == 0:
            logger.debug('Hello reply received from %s', uid)
            self.target_uid = uid
            self.logged = 1
        root = (self.target_uid in self.backend.helper.clients)
        if root  and self.logged == 1:
            logger.debug('Got root object from %s', self.target_uid)
            self.logged = 2
        self.val = (uid and root)
        return self.val

def get_logger(desc):
    '''
    Make a logger for backends.
    Will also be used by backend.py
    '''
    global logger
    import objectsharer as objsh
    logger = objsh.logger
    return logger

def parse_addr(addrstr):
    if type(addrstr) in (types.ListType, types.TupleType):
        return addrstr
    if addrstr.startswith('tcp://'):
        addrstr = addrstr[6:]
    fields = addrstr.split(':')
    if len(fields) != 2:
        return None
    return fields[0], int(fields[1])

class Message(object):
    def __init__(self, sock, sender_uid, parts):
        self.sock = sock
        self.sender_uid = sender_uid
        self.parts = parts

    def __repr__(self):
        return "Message({},{},{})".format(self.sock, self.sender_uid, self.parts)

class Backend(object):
    '''
    General objectsharer backend code.

    All <sock> objects should be the items that can be passed to 'send_msg'
    to send data to a particular client.
    '''

    def __init__(self, helper):
        self.timer = None
        self.uid_to_sock_map = {}   # To send something
        self.uid_to_addr_map = {}   # To send an object by reference
        self.sock_to_uid_map = {}   # For disconnections
        self.addr_to_uid_map = {}   # Server address to uid
        self._timeouts = {}
        self._scheduled_timeouts = []
        self._last_timeout_id = 0
        self.helper = helper
        helper.set_backend(self)
        self.uid = helper.get_object('root')._OS_UID

    def get_uid(self):
        return self.uid

    def connect_from(self, sock, uid, addr):
        '''
        Should be called when a connection is made to associate
        <uid> with <addr>
        '''
        self.uid_to_sock_map[uid] = sock
        self.uid_to_addr_map[uid] = addr
        self.addr_to_uid_map[addr] = uid
        self.sock_to_uid_map[sock] = uid

    def connected_to(self, uid):
        '''
        Return whether we are connected to client identified by <uid>.
        '''
        return uid in self.uid_to_sock_map

    def connected_to_addr(self, addr):
        '''
        Return whether we are connected to client at <addr>.
        '''
        return self.connected_to(self.get_uid_for_addr(addr))

    def get_uid_for_addr(self, addr):
        '''
        Return the uid associated with the objectsharer server at <addr>.
        '''
        return self.addr_to_uid_map.get(addr, None)

    def get_addr_for_uid(self, uid):
        '''
        Return the address for the objectsharer identified by <uid>.
        '''
        for k, v in self.addr_to_uid_map.items():
            if v == uid:
                return k
        return None

    def refresh_connection(self, addr):
        '''
        Refresh a connection by disconnecting and reconnecting to 'addr'.
        '''
        self.forget_connection(addr)
        time.sleep(.01)
        self.connect_to(addr)

    def forget_connection(self, addr, remote=True):
        pass

    def client_disconnected(self, sock):
        '''
        Clean up things related to <sock> if we seem to be disconnected.
        '''
        uid = self.sock_to_uid_map.pop(sock, None)
        logging.info('Removing client %s', uid)
        if uid is None:
            return
        addr = self.uid_to_addr_map.pop(uid, None)
        self.uid_to_sock_map.pop(uid, None)
        self.addr_to_uid_map.pop(addr, None)

    def connect_check(self, addr, uid):
        '''
        Check whether we should proceed to connect to addr.
        Returns True if so, False if we shouldn't (i.e. already are connected).
        '''
        if addr in self.uid_to_addr_map.values():
            logger.warning('Already connected to %s' % addr)
            return False
        if uid is not None and uid in self.uid_to_sock_map:
            logger.warning('Client %s already present at different address' % uid)
            return False
        return True

    def connect_to(self, addr, timeout=20, async=False, uid=None, sock=None):
        '''
        Connect to a remote address <addr>, or, if sock != None, initiate
        messaging to a already connected client.
        '''

        if sock is None:
            if not self.connect_check(addr, uid):
                return False

            # Run back-end specific do_connect()
            sock = self.do_connect(addr)

        # Identify ourselves
        logging.debug('Sending hello_from message to %s', addr)
        msg = ('hello_from', self.get_uid().b, self.get_server_address())
        self.send_msg('dest', [pickle.dumps(msg)], sock=sock)
        if async:
            logging.debug('Waiting for reply asynchronously')
            return

        # Wait for the server to reply.
        # On the server, which received the hello_from first, this should
        # never have to wait.
        if addr not in self.addr_to_uid_map:
            logger.debug('Waiting for hello reply and root object from server...')
            hello = AsyncHelloReply(addr, self)
            self.main_loop(timeout=timeout*1000.0, wait_for=hello)
            if not hello.is_valid():
                raise misc.TimeoutError('Connection to %s timed out; no reply received'%(addr,))

        if addr not in self.addr_to_uid_map:
            raise Exception('UID not resolved!')

        return sock

    def send_msg(self, dest, bufs, sock=None):
        '''
        Send <msg> consisting of parts <bufs> to client <dest> (a uid).
        If <sock> is specified use that socket.
        '''

#        logger.debug('Sending message with %s part(s) to %s', len(bufs), dest)
        if sock is None:
            sock = self.uid_to_sock_map.get(dest, None)
            if sock is None:
                raise Exception('Unable to resolve destination %s' % dest)

        # Determine packet size
        dlen = 7
        for buf in bufs:
            dlen += len(buf) + 4
        if dlen > 0xffffffffL:
            logging.error('Trying to send too long packet: %d', dlen)
            return -1

        b = bytearray(dlen)
        b[:7] = 'OS' + struct.pack('<IB', dlen, len(bufs))
        ofs = 7
        for buf in bufs:
            blen = len(buf)
            b[ofs:ofs+4] = struct.pack('<I', blen)
            b[ofs+4:] = buf
            ofs += blen + 4

        self.send_data_to(sock, b)

###########################################################
# The important functions for backends to implement
###########################################################

    def get_server_address(self):
        '''
        Return the address this server can be reached at.
        '''

    def do_connect(self, addr):
        '''
        Backends should implement connect code here and return a socket (or
        handle) which can be passed to send_msg
        '''
        pass

    def poll(self, timeout):
        '''
        Backends should implement a poll function that checks if data is
        available on any of its sockets. This should return a list on which
        recv_from will be called.
        timeout in seconds.
        '''
        return []

    def recv_from(self, sock):
        '''
        Backends should implement a function that receives a data from <sock>.
        A list of complete packets should be returned.
        '''
        return []

    def send_raw(self, sock, data):
        '''
        Backends should implement sending raw data to <sock>.
        '''
        pass

    def flush_send_queue(self):
        '''
        Backends should overload if they require periodically flushing a
        send queue.
        '''
        pass

###########################################################
# Period callbacks (timeouts)
###########################################################

    def timeout_add(self, delay, func, *args):
        '''
        Schedule a callback within the mainloop. If the function returns
        True it will be rescheduled to occur periodically. If it returns False
        it gets called only once.

        <delay> in msec.
        '''
        self._last_timeout_id += 1
        start = time.time()
        self._timeouts[self._last_timeout_id] = dict(
            start=start,
            delay=delay/1000.0,
            func=func,
            args=args
        )
        bisect.insort(self._scheduled_timeouts, (start+delay/1000.0, self._last_timeout_id))
        return self._last_timeout_id

    def timeout_remove(self, t_id):
        if t_id in self._timeouts:
            del self._timeouts[t_id]

    def _run_timeouts(self):
        now = time.time()
        while len(self._scheduled_timeouts) > 0 and self._scheduled_timeouts[0][0] < now:
            t, t_id = self._scheduled_timeouts.pop(0)
            info = self._timeouts.get(t_id, None)
            if info is None:
                continue

            try:
                ret = info['func'](*info['args'])

                # Only reschedule if returning True
                if not ret:
                    self.timeout_remove(t_id)
                    continue

                # Reschedule
                now2 = time.time()
                delta = (now2 - t) % info['delay']
                t_new = now2 + info['delay'] - delta
                logger.debug('Rescheduling timeout %d for %s', t_id, t_new - now2)
                bisect.insort(self._scheduled_timeouts, (t_new, t_id))
            except Exception, e:
                logger.error('Timeout call %d failed: %s', t_id, str(e))
                self.timeout_remove(t_id)

###########################################################
# Main loop functionality
###########################################################

    def main_loop(self, timeout=None, wait_for=None):
        '''
        Run the receiving main loop for a maximum of <timeout> msec, or
        indefinitely when timeout is None.

        If <wait_for> is specified (a single object or a list), the loop will
        terminate once all objects return True from is_valid().
        '''

        start = time.time()
        if timeout is None:
            endtime = None
        else:
            endtime = start + timeout / 1000.0
#        print 'Main_loop, endttime %s, wait_for = %s' % (endtime, wait_for)

        # Convert wait_for to a list
        if wait_for is not None:
            if type(wait_for) in (types.TupleType, types.ListType):
                wait_for = list(wait_for)
            else:
                wait_for = [wait_for,]

        # If nothing to wait for, flush signal queue
        else:
            self.helper.flush_queue()

        while True:
            # Set curdelay based on end time
            if endtime is not None:
                curdelay = endtime - time.time()
            else:
                curdelay = 10000

            # Adjust curdelay if we have scheduled timeouts
            if len(self._scheduled_timeouts) > 0:
                to_delay = (self._scheduled_timeouts[0][0] - time.time()) * 1000.0
                to_delay = max(0, to_delay)
                curdelay = min(curdelay, to_delay)

            # Flush send queue
            self.flush_send_queue()

            # Poll sockets
            socks = self.poll(max(curdelay,1))
            if len(socks) == 0:
                self._run_timeouts()
                if endtime is not None and time.time() >= endtime:
                    return False
                # Poll again
                continue

            # Handle data on sockets
            waiting = (wait_for is not None)
            msgs = []
            for sock in socks:
                new_msgs = self.recv_from(sock)
                if new_msgs is not None:
                    msgs.extend(new_msgs)

            for msg in msgs:
                try:
                    # Try to look up one more time, as sender uid could
                    # have been provided by first msg in list
                    if msg.sender_uid is None:
                        msg.sender_uid = self.sock_to_uid_map.get(sock, None)

                    self.helper.process_message(msg, waiting=waiting)

                except Exception, e:
                    logger.warning('Failed to process message: %s\n%s', str(e), traceback.format_exc())

            # If we are waiting for call results and have them, return
            if wait_for is not None:
                i = 0
                while i < len(wait_for):
                    if wait_for[i].is_valid():
                        del wait_for[i]
                    else:
                        i += 1
                if len(wait_for) == 0:
                    return True

            # Check whether we timed out
            if endtime is not None and time.time() >= endtime:
                return False
            logger.debug('  Repolling, now %s (curdelay %s)', time.time(), curdelay)

    def _qt_timer(self):
        self.main_loop(timeout=0)
        return True

    def add_qt_timer(self, interval=20):
        '''
        Install a callback timer at <interval> msec to integrate our message
        processing loop into the Qt4 main loop.
        '''

        if self.timer is not None:
            logger.warning('Timer already installed')
            return False

        from PyQt4 import QtCore, QtGui
        _app = QtGui.QApplication.instance()
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL('timeout()'), self._qt_timer)
        self.timer.start(interval)
        return True

