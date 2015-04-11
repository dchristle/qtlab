# ObjectSharer v2 with ZMQ communication backend
# Reinier Heeres <reinier@heeres.eu>, 2013
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
from collections import defaultdict

import logging
import cPickle as pickle
import time
import numpy as np
import inspect
import uuid
import types
import traceback
import misc

# The pickle protocol used; 0 for ASCII, 2 for binary; quite a bit smaller.
PICKLE_PROTO = pickle.HIGHEST_PROTOCOL

# Whether to wrap numpy arrays and transfer the .data object in a binary way
# as a separate message part. From profiling it seems to save cpu time, but
# in real life it does not result in a very big improvement.
WRAP_NPARRAYS = True

# We have the extra DEBUG flag because not doing the logger.debug calls gives
# a significant speed-up
DEBUG = False
if DEBUG:
    LOGLEVEL = logging.DEBUG
else:
    LOGLEVEL = logging.INFO

logger = logging.getLogger("Object Sharer")
logger.setLevel(LOGLEVEL)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
handler.setLevel(LOGLEVEL)
handler.setFormatter(formatter)
logger.addHandler(handler)

DEFAULT_TIMEOUT = 5000      # Timeout in msec
OS_CALL         = 'c'
OS_RETURN       = 'r'
OS_SIGNAL       = 'OS_SIG'

# List of special functions to wrap

SPECIAL_FUNCTIONS = (
    '__getitem__',
    '__setitem__',
    '__delitem__',
    '__contains__',
    '__str__',
    '__repr__',
)

class OSSpecial(object):
    def __init__(self, **kwargs):
        for k, v in kwargs:
            setattr(self, k, v)

#########################################
# Decorators
#########################################

def cache_result(f):
    '''
    Decorator to instruct client to cache function result
    '''
    if not hasattr(f, '_share_options'):
        f._share_options = dict()
    f._share_options['cache_result'] = True
    return f

#########################################
# Asynchronous reply helpers
#########################################

class AsyncReply(object):
    '''
    Container to receive the reply from an asynchoronous call.
    Use is_valid() to see whether the value is valid.
    '''

    def __init__(self, callid, callback=None):
        self._callid = callid
        self.val_valid = False
        self.val = None
        self.callback = callback

    def set(self, val):
        self.val = val
        self.val_valid = True
        if self.callback is not None:
            if DEBUG:
                logger.debug('Performing callback for call id %d' % self._callid)
            try:
                self.callback(val)
            except Exception, e:
                logging.warning('Callback for call %s failed: %s', self._callid, str(e))

    def get(self, block=False, delay=DEFAULT_TIMEOUT, do_raise=True):
        if block and not self.is_valid():
            helper.interact(delay=delay)
        if do_raise and isinstance(self.val, Exception):
            raise self.val
        return self.val

    def is_valid(self):
        return self.val_valid

#########################################
# Helper functions to replace parameters to make transmission possible
# or more efficient.
#########################################

def _walk_objects(obj, func, *args):
    t = type(obj)
    if t in (types.ListType, types.TupleType):
        obj = list(obj)
        for i, v in enumerate(obj):
            obj[i] = _walk_objects(v, func, *args)
    if t is types.DictType:
        for k in sorted(obj):
            obj[k] = _walk_objects(obj[k], func, *args)
    return func(obj, *args)

def _wrap_ars_sobjs(obj, arlist=None):
    '''
    Function to wrap numpy arrays and shared objects for efficient transmission.
    '''
    def replace(o):
        if isinstance(o, np.ndarray):
            if not o.flags['C_CONTIGUOUS']:
                o = np.ascontiguousarray(o)
            assert o.flags['C_CONTIGUOUS']
            arlist.append(o.data)
            return dict(
                OS_AR=True,
                s=o.shape,
                t=o.dtype,
            )
        elif hasattr(o, '_OS_UID'):
            ret = dict(OS_UID=o._OS_UID.b)
            if hasattr(o, '_OS_SRV_ID'):    # Not a local object
                ret['OS_SRV_ID'] = o._OS_SRV_ID
                ret['OS_SRV_ADDR'] = o._OS_SRV_ADDR
            return ret
        return o

    if arlist is None:
        arlist = []
    try:
        obj = _walk_objects(obj, replace)
        return obj, arlist
    except:
        return obj, arlist

def _unwrap_ars_sobjs(obj, bufs, client=None):
    '''
    Function to unwrap numpy arrays and shared objects after efficient
    transmission.
    '''

    def replace(o):
        if type(o) is types.DictType:
            if 'OS_AR' in o:
                if len(bufs) == 0:
                    raise ValueError('No buffer!')
                ar = np.frombuffer(
                    bufs.pop(0),
                    dtype=o['t']
                )
                ar = ar.reshape(o['s'])
                return ar
            if 'OS_UID' in o:
                if 'OS_SRV_ID' in o and 'OS_SRV_ADDR' in o:
                    return helper.get_object_from(o['OS_UID'], o['OS_SRV_ID'], o['OS_SRV_ADDR'])
                else:
                    return helper.get_object_from(o['OS_UID'], client)
        return o

    obj = _walk_objects(obj, replace)
    return obj, bufs

def _wrap_sobjs(obj, arlist=None):
    '''
    Function to shared objects only.
    '''
    def replace(o):
        if hasattr(o, '_OS_UID'):
            ret = dict(OS_UID=o._OS_UID.b)
            if hasattr(o, '_OS_SRV_ID'):    # Not a local object
                ret['OS_SRV_ID'] = o._OS_SRV_ID
                ret['OS_SRV_ADDR'] = o._OS_SRV_ADDR
            return ret
        return o

    if arlist is None:
        arlist = []
    try:
        obj = _walk_objects(obj, replace)
        return obj, arlist
    except:
        return obj, arlist

def _unwrap_sobjs(obj, bufs, client=None):
    '''
    Function to unwrap shared objects only.
    '''

    def replace(o):
        if type(o) is types.DictType and 'OS_UID' in o:
            if 'OS_SRV_ID' in o and 'OS_SRV_ADDR' in o:
                return helper.get_object_from(o['OS_UID'], o['OS_SRV_ID'], o['OS_SRV_ADDR'])
            else:
                return helper.get_object_from(o['OS_UID'], client)
        return o

    obj = _walk_objects(obj, replace)
    return obj, bufs

if WRAP_NPARRAYS:
    _wrap = _wrap_ars_sobjs
    _unwrap = _unwrap_ars_sobjs
else:
    _wrap = _wrap_sobjs
    _unwrap = _unwrap_sobjs

#########################################
# Object sharer core
#########################################

class ObjectSharer(object):
    '''
    The object sharer core.
    '''

    def __init__(self):
        self.sock = None
        self.backend = None
        self.root_uid = None

        # Local objects
        self.objects = {}
        self.name_map = {}

        # Clients, proxies and remote object lists
        self.clients = {}
        self._proxy_cache = {}
        self._client_object_list_cache = {}

        self._last_call_id = 0
        self.reply_objects = {}

        # Signal related
        self._last_hid = 0
        self._callbacks_hid = {}
        self._callbacks_name = {}
        self._signal_queue = []

    def set_backend(self, backend):
        self.backend = backend

    def interact(self, delay=DEFAULT_TIMEOUT, wait_for=None):
        self.backend.main_loop(delay=delay, wait_for=wait_for)

    def call(self, client, objuid, func_name, *args, **kwargs):
        is_signal = kwargs.get(OS_SIGNAL, False)
        callback = kwargs.pop('callback', None)
        async = kwargs.pop('async', False) or (callback is not None) or is_signal
        timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT)

        self._last_call_id += 1
        callid = self._last_call_id
        async_reply = AsyncReply(callid, callback=callback)
        self.reply_objects[callid] = async_reply
        if DEBUG:
            logger.debug('Sending call %d to %s: %s.%s(%s,%s), async=%s', callid, client, objuid, func_name, misc.ellipsize(str(args)), misc.ellipsize(str(kwargs)), async)

        args, arlist = _wrap(args)
        kwargs, arlist = _wrap(kwargs, arlist)
        msg = (
            OS_CALL,
            callid,
            objuid.b,
            func_name,
            args,
            kwargs
        )
        try:
            msg = pickle.dumps(msg, PICKLE_PROTO)
        except:
            raise Exception('Unable to pickle function call: %s' % str(msg))
        arlist.insert(0, msg)
        self.backend.send_msg(client, arlist)

        if async:
            return async_reply

        ret = self.backend.main_loop(timeout=timeout, wait_for=async_reply)
        if ret:
            val = async_reply.get()
            return val
        else:
            raise misc.TimeoutError('Call timed out')

    #####################################
    # Object resolving functions.
    #####################################

    def list_objects(self):
        '''
        Return a list of locally available objects, comprising of both the uids
        and the aliases.
        '''
        ret = list(self.objects.keys())
        ret.extend(self.name_map.keys())
        return ret

    def get_object(self, objid):
        '''
        Get a local object.
        <objid> can be either a uid or an alias.
        '''

        # Direct uid look-up
        if isinstance(objid, misc.UID):
            return self.objects.get(objid, None)

        # Look-up alias in name_map
        objid = self.name_map.get(objid, objid)
        # Look-up in objects list
        return self.objects.get(objid, None)

    def _get_object_shared_props_funcs(self, obj):
        props = []
        funcs = []
        for key, val in inspect.getmembers(obj):
            if key.startswith('_') and not key in SPECIAL_FUNCTIONS:
                continue
            if key == 'connect':
                continue
            elif callable(val):
                if hasattr(val, '_share_options'):
                    opts = val._share_options
                else:
                    opts = {}
                opts['__doc__'] = getattr(val, '__doc__', None)
                try:
                    opts['__argspec__'] = inspect.getargspec(val)
                except:
                    opts['__argspec__'] = None
                funcs.append((key, opts))
            else:
                props.append(key)

        return props, funcs

    def get_object_info(self, objid):
        '''
        Return the object info of a local object to build a proxy remotely.
        <objid> can be either a uid or an alias.
        '''

        obj = self.get_object(objid)
        if obj is None:
            return None

        props, funcs = self._get_object_shared_props_funcs(obj)
        info = dict(
            uid=obj._OS_UID.b,
            properties=props,
            functions=funcs
        )
        return info

    def get_object_info_from(self, objid, client_id, client_addr=None):
        '''
        Get object info from a particular client.
        If not connected yet, do that first.
        '''

        # Handle clients that we are not yet connected to.
        if client_id not in self.clients:
            if client_addr is None:
                logger.warning('Object from unknown client requested')
                return None
            try:
                objid.encode('ascii')
                objid_s = objid
            except UnicodeError:
                objid_s = str(misc.UID(objid))
            logger.info('Object %s requested from unconnected client %s @ %s, connecting...', objid_s, client_id, client_addr)
            self.backend.connect_to(client_addr, uid=client_id)

        # We should be connected now
        if client_id not in self.clients:
            logger.error('Unable to connect to client')
            return None

        try:
            return self.clients[client_id].get_object_info(objid)
        except misc.TimeoutError:
            logger.warning('Client %s unresponsive: Removing from connected' % client_id)
            del self.clients[client_id] # I'm trying to think of a better place to do client invalidation!
            return None

    def get_object_from(self, objid, client_id, client_addr=None, no_cache=False):
        '''
        Get an object from a particular client.
        If a proxy is available in cache return that
        If not connected yet, do that first.
        <objid> can be either a uid or an alias.
        '''

        # Return from cache if it is the right object (it could be an object
        # with the same alias at a different location),
        if not no_cache:
            if objid in self._proxy_cache and self._proxy_cache[objid]._OS_SRV_ID == client_id:
                return self._proxy_cache[objid]

        info = self.get_object_info_from(objid, client_id, client_addr=client_addr)
        if info is None:
            return None
        proxy = ObjectProxy(client_id, info)
        self._proxy_cache[objid] = proxy
        self._proxy_cache[proxy.os_get_uid()] = proxy
        return proxy

    def find_object(self, objname, client_id=None, client_addr=None, no_cache=False):
        '''
        Find a particular object either locally or with a client.
        '''

        if client_id is not None:
            return self.get_object_from(objname, client_id, client_addr)

        # A local object?
        obj = self.get_object(objname)
        if obj is not None:
            return obj
        if not no_cache:
            # A remote object with cached proxy?
            if objname in self._proxy_cache:
                return self._proxy_cache[objname]

            # See if we already know which client has this object
            for client_id, names in self._client_object_list_cache.items():
                if objname in names:
                    return self.get_object_from(objname, client_id)

        # Query all clients
        # TODO: asynchronously
        for client_id in self.clients.keys():
            obj = self.get_object_from(objname, client_id, no_cache=no_cache)
            if obj is not None:
                return obj
        return None

    def register(self, obj, name=None):
        '''
        This function registers an object as a shared object.

        - Generates a unique id (<obj>.OS_UID)
        - Adds an emit function (<obj>.emit), which can be used to emit
        signals. A previously available emit function will still be called.
        '''

        if obj is None:
            return
        if hasattr(obj, '_OS_UID') and obj._OS_UID is not None:
            logger.warning('Object %s already registered' % obj._OS_UID)
            return

        obj._OS_UID = misc.UID(bytes=uuid.uuid4().bytes)
        logging.info('New object (alias %s) with UID %s registered', name, obj._OS_UID)
        if name is not None:
            if name in self.name_map:
                raise Exception('Object %s already defined' % name)
            self.name_map[name] = obj._OS_UID
            if name == 'root':
                logging.info('Root UID set to %s', obj._OS_UID)
                self.root_uid = obj._OS_UID

        obj._OS_emit = getattr(obj, 'emit', None)
        # TODO: make obj properly assigned
        obj.emit = lambda signal, *args, **kwargs: self.emit_signal(obj._OS_UID.b, signal, *args, **kwargs)
        obj.connect = lambda signame, callback, *args, **kwargs: self.connect_signal(obj._OS_UID, signame, callback, *args, **kwargs)
        self.objects[obj._OS_UID] = obj

        root.emit('object-added', obj._OS_UID, name=name)

    def unregister(self, obj):
        if not hasattr(obj, '_OS_UID'):
            logger.warning('Trying to unregister an unknown object')

        if obj._OS_UID in self.objects:
            del self.objects[obj._OS_UID]
            root.emit('object-removed', obj._OS_UID)

        for name, id in self.name_map.items():
            if obj._OS_UID == id:
                del self.name_map[name]

    #####################################
    # Signal functions
    #####################################

    def connect_signal(self, uid, signame, callback, *args, **kwargs):
        '''
        Called by ObjectProxy instances to register a callback request.
        '''
        self._last_hid += 1
        info = {
                'hid': self._last_hid,
                'uid': uid,
                'signal': signame,
                'callback': callback,
                'args': args,
                'kwargs': kwargs,
        }

        self._callbacks_hid[self._last_hid] = info
        name = '%s__%s' % (uid, signame)
        if name in self._callbacks_name:
            self._callbacks_name[name].append(info)
        else:
            self._callbacks_name[name] = [info]

        return self._last_hid

    def disconnect_signal(self, hid):
        if hid in self._callbacks_hid:
            del self._callbacks_hid[hid]

        for name, info_list in self._callbacks_name.items():
            for index, info in enumerate(info_list):
                if info['hid'] == hid:
                    del self._callbacks_name[name][index]
                    break

    def emit_signal(self, uid, signame, *args, **kwargs):
        uid = misc.UID(uid)
        if DEBUG:
            logger.debug('Emitting %s(%r, %r) for %s to %d clients',
                signame, args, kwargs, uid, len(self.clients))

        kwargs[OS_SIGNAL] = True
        for client in self.clients.values():
#            print 'Calling receive sig, uid=%s, signame %s, args %s, kwargs %s' % (uid, signame, args, kwargs)
            client.receive_signal(uid, signame, *args, **kwargs)
        self.receive_signal(uid, signame, *args, **kwargs)

    def receive_signal(self, uid, signame, *args, **kwargs):
        kwargs.pop(OS_SIGNAL, None)
        if DEBUG:
            logger.debug('Received signal %s(%r, %r) from %s',
                signame, args, kwargs, uid)

        ncalls = 0
        start = time.time()
        name = '%s__%s' % (uid, signame)
        if name in self._callbacks_name:
            info_list = self._callbacks_name[name]
            for info in info_list:

                try:
                    fargs = list(args)
                    fargs.extend(info['args'])
                    fkwargs = kwargs.copy()
                    fkwargs.update(info['kwargs'])
                    info['callback'](*fargs, **fkwargs)
                except Exception, e:
                    logger.warning('Callback to %s failed for %s.%s: %s\n%s',
                            info.get('callback', None), uid, signame, str(e), traceback.format_exc())

        end = time.time()
        if DEBUG:
            logger.debug('Did %d callbacks in %.03fms for sig %s',
                ncalls, (end - start) * 1000, signame)

    #####################################
    # Client management
    #####################################

    def _update_client_object_list(self, uid, names):
        if names is not None:
            self._client_object_list_cache[uid] = names

    def _add_client_to_list(self, uid, root_info):
        if root_info is None:
            raise Exception('Unable to retrieve root object from %s' % uid)
        if DEBUG:
            logger.debug('  root@%s.get_object_info() reply: %s', uid, root_info)
        self.clients[uid] = ObjectProxy(uid, root_info)
        self.clients[uid].list_objects(callback=lambda reply, uid=uid:
            self._update_client_object_list(uid, reply))

    def request_client_proxy(self, uid, async=False):
        '''
        Request the root object from a client to construct the proxy.
        '''
        if not async:
            info = self.call(uid, uid, 'get_object_info', 'root')
            self._add_client_to_list(uid, info)
        else:
            self.call(uid, uid, 'get_object_info', 'root', callback=lambda reply, uid=uid:
                self._add_client_to_list(uid, reply))

    def client_disconnected(self, uid):
        logger.info("Client %s disconnected, remove from clients map", uid)
        if uid in self.clients:
            del self.clients[uid]
        if uid in ObjectProxy.uid_to_proxy_map:
            for p in ObjectProxy.uid_to_proxy_map[uid]:
                p._client_disconnected()
            del ObjectProxy.uid_to_proxy_map[uid]

    #####################################
    # Message processing
    #####################################

    def process_message(self, msg, waiting=False):
        '''
        Process a remote message.
        <msg> is a backend.Message object

        If <waiting> is True it indicates a main loop is waiting for something,
        in which case signals get queued.
        '''

        # Decode message
        try:
            info = pickle.loads(msg.parts[0])
            if DEBUG:
                logger.debug('Msg %s from %s: %s', info[0], msg.sender_uid, info)
        except Exception, e:
            logger.warning('Unable to decode object: %s [%r]', str(e), msg.parts[0])
            return

        if info[0] == OS_CALL:
            # In a try statement to postpone checks
            try:
#            if 1:
                (callid, objid, funcname, args, kwargs) = info[1:6]
                objid = misc.UID(bytes=objid)
                sig = kwargs.get(OS_SIGNAL, False)

                # Store signals if waiting a reply or event
                if waiting and sig:
                    self._signal_queue.append(msg)
                    return

                # Unwrap arguments
                try:
                    bufs = msg.parts[1:]
                    args, bufs = _unwrap(args, bufs, msg.sender_uid)
                    kwargs, bufs = _unwrap(kwargs, bufs, msg.sender_uid)
                except:
                    ret = misc.RemoteException('Unable to unwrap objects')
                    reply = [pickle.dumps((OS_RETURN, callid, ret), PICKLE_PROTO)]
                    self.backend.send_msg(msg.sender_uid, reply)
                    return

                if DEBUG:
                    logger.debug('  Processing call %s: %s.%s(%s,%s)', callid, objid, funcname, args, kwargs)

                # Call function
                obj = self.get_object(objid)
                func = getattr(obj, funcname, None)
                ret = func(*args, **kwargs)

                # If a signal, no need to return anything to caller
                if sig:
                    return

                # Wrap return value
                ret, bufs = _wrap(ret)
                if DEBUG:
                    logger.debug('  Returning for call %s: %s', callid, misc.ellipsize(str(ret)))

            # Handle errors
            except Exception, e:
#            if 0:
                if len(info) < 6:
                    logger.error('Invalid call msg: %s', info)
                    ret = misc.RemoteException('Invalid call msg')
                elif 'obj' not in locals() or obj is None:
                    ret = misc.RemoteException('Object %s not available for calls' % objid)
                elif 'func' not in locals() or func is None:
                    ret = misc.RemoteException('Object %s does not have function %s' % (objid, funcname))
                else:
                    tb = traceback.format_exc(15)
                    ret = misc.RemoteException('%s\n%s' % (e, tb))

            # Prepare return packet
            try:
                reply = [pickle.dumps((OS_RETURN, callid, ret), PICKLE_PROTO)]
                reply.extend(bufs)
            except:
                ret = misc.RemoteException('Unable to pickle return %s' % str(ret))
                reply = [pickle.dumps((OS_RETURN, callid, ret), PICKLE_PROTO)]
            self.backend.send_msg(msg.sender_uid, reply)

        elif info[0] == OS_RETURN:
            if len(info) < 3:
                return Exception('Invalid return msg')

            # Get call id and unwrap return value
            callid, ret = info[1:3]
            ret, bufs = _unwrap(ret, msg.parts[1:], msg.sender_uid)

            if DEBUG:
                logger.debug('  Processing return for %s: %s', callid, ret)
            if callid in self.reply_objects:
                self.reply_objects[callid].set(ret)
                # We should not keep track of the reply object
                del self.reply_objects[callid]
            else:
                raise Exception('Reply for unkown call %s', callid)

        elif info[0] == 'hello_from':
            msg.sender_uid = misc.UID(bytes=info[1])
            from_addr = info[2]
            logger.debug('hello_from client %s with server @ %s', msg.sender_uid, from_addr)
            self.backend.connect_from(msg.sock, msg.sender_uid, from_addr)
# This was necessary for ZMQ sockets
#            if not self.backend.connected_to(msg.sender_uid):
#                if DEBUG:logger.debug('Initiating reverse connection...')
#                self.backend.connect_to(from_addr, msg.sender_uid)
            if DEBUG:
                logger.debug('Sending hello_reply')
            reply = ('hello_reply', self.root_uid.b, self.backend.get_server_address())
            self.backend.send_msg(msg.sender_uid, [pickle.dumps(reply, PICKLE_PROTO)])
            self.request_client_proxy(msg.sender_uid, async=True)

        elif info[0] == 'hello_reply':
            msg.sender_uid = misc.UID(bytes=info[1])
            from_addr = info[2]
            if DEBUG:
                logger.debug('hello_reply client %s with server @ %s', msg.sender_uid, from_addr)
            self.backend.connect_from(msg.sock, msg.sender_uid, from_addr)
            self.request_client_proxy(msg.sender_uid, async=True)

        elif info[0] == 'goodbye_from':
            if DEBUG:
                logger.debug('Goodbye client %s from %s', msg.sender_uid, info[1])
            forget_uid = self.backend.get_uid_for_addr(info[1])
            if forget_uid in self.clients:
                del self.clients[forget_uid]
                if DEBUG:
                    logger.debug('deleting client %s', forget_uid)
            self.backend.forget_connection(info[1], remote=False)
            if msg.sender_uid in self.clients:
                del self.clients[msg.sender_uid]
                if DEBUG:
                    logger.debug('deleting client %s', msg.sender_uid)

        # Ping - pong to check alive
        elif info[0] == 'ping':
            logger.info('PING from %s', msg.sender_uid)
            msg = pickle.pickle(('pong',), PICKLE_PROTO)
            self.backend.send_msg(msg.sender_uid, [msg])
        elif info[0] == 'pong':
            logger.info('PONG from %s', msg.sender_uid)

        else:
            logger.warning('Unknown msg: %s', info)

    def flush_queue(self, nmax=5):
        '''
        Process a maximum on <nmax> queued signals.
        Return True if signal queue empty when returning.
        '''
        i = 0
        while i < nmax and len(self._signal_queue) > 0:
            msg = self._signal_queue.pop(0)
            self.process_message(msg)
            i += 1
        return (len(self._signal_queue) == 0)

class RootObject(object):
    '''
    Every program using shared objects should have an instance of RootObject.
    This object exposes functions of the ObjectSharer instance called helper.
    '''

    def __init__(self):
        pass

    def hello_world(self):
        return 'Hello world!'

    def hello_exception(self):
        return 1 / 0

    def client_announce(self, name):
        helper.add_client(name)

    def list_objects(self):
        return helper.list_objects()

    def get_object_info(self, objname):
        return helper.get_object_info(objname)

    def receive_signal(self, uid, signame, *args, **kwargs):
        helper.receive_signal(uid, signame, *args, **kwargs)

class _FunctionCall():

    def __init__(self, client, objname, funcname, share_options):
        self._client = client
        self._objname = objname
        self._funcname = funcname

        if share_options is None:
            self._share_options = {}
        else:
            self._share_options = share_options

        # Setup doc string, including remote function name and parameters
        doc = funcname
        argspec = self._share_options.get('__argspec__', None)
        if argspec:
            doc += inspect.formatargspec(*argspec) + '\n'
        else:
            doc += '()\n'

        docstr = self._share_options.get('__doc__', '')
        if docstr:
            doc += docstr
        setattr(self, '__doc__', doc)

        self._cached_result = None

    def __call__(self, *args, **kwargs):
        cache = self._share_options.get('cache_result', False)
        if cache and self._cached_result is not None:
            return self._cached_result

        ret = helper.call(self._client, self._objname, self._funcname, *args, **kwargs)
        if cache:
            self._cached_result = ret

        return ret

class ObjectProxy(object):
    '''
    Client side object proxy.

    Based on the info dictionary this object will be populated with functions
    and properties that are available on the remote object.
    '''

    PROXY_CACHE = {}
    uid_to_proxy_map = defaultdict(lambda: [])
    def __new__TODO(cls, client, uid, info=None, newinst=False):
        if info is None:
            return None
        if info['uid'] in ObjectProxy.PROXY_CACHE:
            return ObjectProxy.PROXY_CACHE[info['uid']]
        else:
            return super(ObjectProxy, cls).__new__(client, uid, info, newinst)

    def __init__(self, client, info):
        self._OS_UID = misc.UID(bytes=info['uid'])
        self._OS_SRV_ID = client
        self._OS_SRV_ADDR = helper.backend.get_addr_for_uid(client)
        ObjectProxy.uid_to_proxy_map[self._OS_SRV_ID].append(self)
        self.__new_hid = 1
        self._specials = {}
        self.__initialize(info)
        self._disconnect_actions = []

    def __getitem__(self, key):
        func = self._specials.get('__getitem__', None)
        if func is None:
            raise Exception('Object does not support indexing')
        return func(key)

    def __setitem__(self, key, val):
        func = self._specials.get('__setitem__', None)
        if func is None:
            raise Exception('Object does not support indexing')
        return func(key, val)

    def __delitem__(self, key): #TODO: make this less copy/paste
        func = self._specials.get('__delitem__', None)
        if func is None:
            raise Exception('Object does not support indexing')
        return func(key)

    def __contains__(self, key):
        func = self._specials.get('__contains__', None)
        if func is None:
            raise Exception('Object does not implement __contains__')
        return func(key)

    def __str__(self):
        s = 'ObjectProxy for %s @ %s (address %s)' % (self._OS_UID, self._OS_SRV_ID, self._OS_SRV_ADDR)
        func = self._specials.get('__str__', None)
        if func:
            s += '\nRemote info:\n%s' % (func(),)
        return s

    def __repr__(self):
        func = self._specials.get('__str__', None)
        s = 'ObjectProxy(%s)' % (self._OS_UID,)
        if func:
            s += ': %s' % (func(), )
        return s

    def __initialize(self, info):
        if info is None:
            return

        for funcname, share_options in info['functions']:
            func = _FunctionCall(self._OS_SRV_ID, self._OS_UID, funcname, share_options)
            if funcname in SPECIAL_FUNCTIONS:
                self._specials[funcname] = func
            else:
                setattr(self, funcname, func)

        for propname in info['properties']:
            setattr(self, propname, 'blaat')

    def connect(self, signame, func):
        return helper.connect_signal(self._OS_UID, signame, func)

    def disconnect(self, hid):
        return helper.disconnect_signal(hid)

    def on_disconnect(self, fn):
        """
        Run <fn> when the client this is proxied from is disconnected
        """
        self._disconnect_actions.append(fn)

    def _client_disconnected(self):
        logger.info("client server to %s lost, running %d actions" % (self._OS_UID, len(self._disconnect_actions)))
        for fn in self._disconnect_actions:
            fn()

    def os_get_client(self):
        return self._OS_SRV_ID

    def os_get_uid(self):
        return self._OS_UID

def set_backend(be):
    '''
    Initialize objectsharer using appropriate backend.
    '''
    global backend

    if be == 'socket':
        import socketbackend
        backend = socketbackend.SocketBackend(helper)
    else:
        raise Exception('Unknown backend %s' % backend)

def add_os_args(args):
    args.add_option('osbackend', type=str,
        help='Objectsharer backend, socket (default) or zmq')

helper = ObjectSharer()
register = helper.register
find_object = helper.find_object

root = RootObject()
register(root, name='root')
set_backend('socket')

