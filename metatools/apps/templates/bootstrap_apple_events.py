"""
This file is derived from Py2App's argv_emulation, whose license is found below.
"""
"""
This is the MIT license. This software may also be distributed under the same 
terms as Python (the PSF license).

Copyright (c) 2004 Bob Ippolito.

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.


sys.argv emulation

This module starts a basic event loop to collect file- and url-open AppleEvents. Those get
converted to strings and stuffed into sys.argv. When that is done we continue starting
the application.

This is a workaround to convert scripts that expect filenames on the command-line to work
in a GUI environment. GUI applications should not use this feature.

NOTE: This module uses ctypes and not the Carbon modules in the stdlib because the latter
don't work in 64-bit mode and are also not available with python 3.x.
"""

import ctypes
import functools
import os
import struct
import sys
import time


class AEDesc(ctypes.Structure):
    _fields_ = [
        ('descKey', ctypes.c_int),
        ('descContent', ctypes.c_void_p),
    ]

class EventTypeSpec(ctypes.Structure):
    _fields_ = [
        ('eventClass',      ctypes.c_int),
        ('eventKind',       ctypes.c_uint),
    ]


carbon = ctypes.CDLL('/System/Library/Carbon.framework/Carbon')

timer_func = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_long)

ae_callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p)

carbon.AEInstallEventHandler.argtypes = [
        ctypes.c_int, ctypes.c_int, ae_callback,
        ctypes.c_void_p, ctypes.c_char ]

carbon.AERemoveEventHandler.argtypes = [
        ctypes.c_int, ctypes.c_int, ae_callback,
        ctypes.c_char ]

carbon.AEProcessEvent.restype = ctypes.c_int
carbon.AEProcessEvent.argtypes = [ctypes.c_void_p]


carbon.ReceiveNextEvent.restype = ctypes.c_int
carbon.ReceiveNextEvent.argtypes = [
    ctypes.c_long,  ctypes.POINTER(EventTypeSpec),
    ctypes.c_double, ctypes.c_char,
    ctypes.POINTER(ctypes.c_void_p)
]


carbon.AEGetParamDesc.restype = ctypes.c_int
carbon.AEGetParamDesc.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
        ctypes.POINTER(AEDesc)]

carbon.AECountItems.restype = ctypes.c_int
carbon.AECountItems.argtypes = [ ctypes.POINTER(AEDesc),
        ctypes.POINTER(ctypes.c_long) ]

carbon.AEGetNthDesc.restype = ctypes.c_int
carbon.AEGetNthDesc.argtypes = [
        ctypes.c_void_p, ctypes.c_long, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p ]

carbon.AEGetDescDataSize.restype = ctypes.c_int
carbon.AEGetDescDataSize.argtypes = [ ctypes.POINTER(AEDesc) ]

carbon.AEGetDescData.restype = ctypes.c_int
carbon.AEGetDescData.argtypes = [
        ctypes.POINTER(AEDesc),
        ctypes.c_void_p,
        ctypes.c_int,
        ]


carbon.FSRefMakePath.restype = ctypes.c_int
carbon.FSRefMakePath.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]


# Configure AppleEvent handlers
ae_callback = carbon.AEInstallEventHandler.argtypes[2]

kAEInternetSuite,   = struct.unpack('>i', b'GURL')
kAEISGetURL,        = struct.unpack('>i', b'GURL')
kCoreEventClass,    = struct.unpack('>i', b'aevt')
kAEOpenApplication, = struct.unpack('>i', b'oapp')
kAEOpenDocuments,   = struct.unpack('>i', b'odoc')
keyDirectObject,    = struct.unpack('>i', b'----')
typeAEList,         = struct.unpack('>i', b'list')
typeChar,           = struct.unpack('>i', b'TEXT')
typeFSRef,          = struct.unpack('>i', b'fsrf')
FALSE               = b'\0'
TRUE                = b'\1'
eventLoopTimedOutErr = -9875

kEventClassAppleEvent, = struct.unpack('>i', b'eppc')
kEventAppleEvent = 1



class AppleEventHandler(object):

    def __init__(self):

        self._count = 0

        self._wrapped_on_open_app  = ae_callback(self._on_open_app)
        self._wrapped_on_open_file = ae_callback(self._on_open_file)
        self._wrapped_on_open_url  = ae_callback(self._on_open_url)

        carbon.AEInstallEventHandler(kCoreEventClass, kAEOpenApplication,
                self._wrapped_on_open_app, 0, FALSE)
        carbon.AEInstallEventHandler(kCoreEventClass, kAEOpenDocuments,
                self._wrapped_on_open_file, 0, FALSE)
        carbon.AEInstallEventHandler(kAEInternetSuite, kAEISGetURL,
                self._wrapped_on_open_url, 0, FALSE)

    def close(self):
        carbon.AERemoveEventHandler(kCoreEventClass, kAEOpenApplication,
                self._wrapped_on_open_app, FALSE)
        carbon.AERemoveEventHandler(kCoreEventClass, kAEOpenDocuments,
                self._wrapped_on_open_file, FALSE)
        carbon.AERemoveEventHandler(kAEInternetSuite, kAEISGetURL,
                self._wrapped_on_open_url, FALSE)

    def loop(self, count=None, timeout=None):

        start = time.time()
        now = time.time()

        eventType = EventTypeSpec()
        eventType.eventClass = kEventClassAppleEvent
        eventType.eventKind = kEventAppleEvent

        while (count is None or self._count < count) and (timeout is None or now - start < timeout):

            event = ctypes.c_void_p()
            status = carbon.ReceiveNextEvent(1, ctypes.byref(eventType),
                    start + timeout - now if timeout else 60.0, TRUE, ctypes.byref(event))

            if status == eventLoopTimedOutErr:
                break

            elif status != 0:
                print("argvemulator warning: fetching events failed")
                break

            status = carbon.AEProcessEvent(event)
            if status != 0:
                print("argvemulator warning: processing events failed")
                break

    def emulate_argv(self, timeout=60.0):

        # Remove the funny -psn_xxx_xxx argument
        if len(sys.argv) > 1 and sys.argv[1].startswith('-psn_'):
            del sys.argv[1]

        self.loop(count=1, timeout=timeout)

    def _on_open_app(self, message, reply, refcon):
        # Got a kAEOpenApplication event, which means we can
        # start up. On some OSX versions this event is even
        # sent when an kAEOpenDocuments or kAEOpenURLs event
        # is sent later on.
        #
        # Therefore don't set running to false, but reduce the
        # timeout to at most two seconds beyond the current time.
        # self.timeout = min(self.timeout, time.time() - self.start + 2)

        # WesternX: On our OSXes, this is delivered after the URL or File is.
        self._count += 1
        return 0

    def _on_open_file(self, message, reply, refcon):
        listdesc = AEDesc()
        sts = carbon.AEGetParamDesc(message, keyDirectObject, typeAEList,
                ctypes.byref(listdesc))
        if sts != 0:
            print("argvemulator warning: cannot unpack open document event")
            self.running = False
            return

        item_count = ctypes.c_long()
        sts = carbon.AECountItems(ctypes.byref(listdesc), ctypes.byref(item_count))
        if sts != 0:
            print("argvemulator warning: cannot unpack open document event")
            self.running = False
            return

        desc = AEDesc()
        for i in range(item_count.value):
            sts = carbon.AEGetNthDesc(ctypes.byref(listdesc), i+1, typeFSRef, 0, ctypes.byref(desc))
            if sts != 0:
                print("argvemulator warning: cannot unpack open document event")
                self.running = False
                return

            sz = carbon.AEGetDescDataSize(ctypes.byref(desc))
            buf = ctypes.create_string_buffer(sz)
            sts = carbon.AEGetDescData(ctypes.byref(desc), buf, sz)
            if sts != 0:
                print("argvemulator warning: cannot extract open document event")
                continue

            fsref = buf

            buf = ctypes.create_string_buffer(1024)
            sts = carbon.FSRefMakePath(ctypes.byref(fsref), buf, 1023)
            if sts != 0:
                print("argvemulator warning: cannot extract open document event")
                continue

            if sys.version_info[0] > 2:
                self.on_open_file(buf.value.decode('utf-8'))
            else:
                self.on_open_file(buf.value)

        self._count += 1
        return 0

    def _on_open_url(self, message, reply, refcon):
        listdesc = AEDesc()
        ok = carbon.AEGetParamDesc(message, keyDirectObject, typeAEList,
                ctypes.byref(listdesc))
        if ok != 0:
            print("argvemulator warning: cannot unpack open document event")
            self.running = False
            return

        item_count = ctypes.c_long()
        sts = carbon.AECountItems(ctypes.byref(listdesc), ctypes.byref(item_count))
        if sts != 0:
            print("argvemulator warning: cannot unpack open url event")
            self.running = False
            return

        desc = AEDesc()
        for i in range(item_count.value):
            sts = carbon.AEGetNthDesc(ctypes.byref(listdesc), i+1, typeChar, 0, ctypes.byref(desc))
            if sts != 0:
                print("argvemulator warning: cannot unpack open URL event")
                self.running = False
                return

            sz = carbon.AEGetDescDataSize(ctypes.byref(desc))
            buf = ctypes.create_string_buffer(sz)
            sts = carbon.AEGetDescData(ctypes.byref(desc), buf, sz)
            if sts != 0:
                print("argvemulator warning: cannot extract open URL event")

            else:
                if sys.version_info[0] > 2:
                    self.on_open_url(buf.value.decode('utf-8'))
                else:
                    self.on_open_url(buf.value)

        self._count += 1
        return 0

    def on_open_file(self, path):
        sys.argv.append(path)

    def on_open_url(self, url):
        sys.argv.append(url)





