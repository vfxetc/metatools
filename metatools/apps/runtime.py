import functools
import site
import struct
import sys
import warnings

from ..moduleproxy import ModuleProxy

extras = '/System/Library/Frameworks/Python.framework/Versions/Current/Extras/lib/python'
site.addsitedir(extras)

from PyObjCTools import AppHelper
import AppKit
import CoreFoundation
import Foundation
import objc


NS = ModuleProxy(['NS'], [Foundation, AppKit])
CF = ModuleProxy(['CF'], [CoreFoundation])


HANDLE_APPLE_EVENTS = False

_has_already_done = set()
def _already_done(name):
    if name in _has_already_done:
        return True
    _has_already_done.add(name)


def on_app_event(func=None, name=None):
    if func is None:
        return functools.partial(on_app_event, name=name)
    WXAppDelegate._callbacks.setdefault(name or func.__name__, []).append(func)
    return func


# These classes exist in a global namespace, so we need something unique.
class WXAppDelegate(NS.Object):

    _instance = None
    _callbacks = {}
    _next = None

    @classmethod
    def instance(cls):
        obj = cls._instance
        if not obj:
            obj = cls._instance = cls.alloc().init()
            obj._init()
        return obj

    def _init(self):
        self._next = NS.App.delegate()
        NS.App.setDelegate_(self)
        if HANDLE_APPLE_EVENTS: # In development.
            apple_event_manager = NS.AppleEventManager.sharedAppleEventManager()
            apple_event_manager.setEventHandler_andSelector_forEventClass_andEventID_(
                self,
                self.handleGetURLEvent_withReplyEvent_,
                struct.unpack('>i', b'GURL')[0], # kInternetEventClass,
                struct.unpack('>i', b'GURL')[0], # kAEGetURL
            )

    def applicationWillFinishLaunching_(self, notification):
        delegate = NS.App.delegate()
        if delegate is not self:
            # Seems like Qt has replaced us as the delegate.
            # They don't seem to forward the notifications that we want,
            # so we need to take over (again).
            self._init()

    def applicationDidFinishLaunching_(self, notification):
        
        # If we launched due to a user notification, pass it to the normal handler.
        user_info = notification.userInfo()
        user_notification = user_info and user_info.objectForKey_("NSApplicationLaunchUserNotificationKey")
        if user_notification:
            self.userNotificationCenter_didActivateNotification_(
                NS.UserNotificationCenter.defaultUserNotificationCenter(),
                user_notification
            )
        
        # If we replaced a delegate, call it too.
        if self._next:
            self._next.applicationDidFinishLaunching_(notification)

    def handleGetURLEvent_withReplyEvent_(self, event, reply):
        print 'handleGetURLEvent_withReplyEvent_', event, reply



_default_identifier = 'com.westernx.metatools'
def replace_bundle_id(bundle_id=None, reason=None):

    bundle_id = bundle_id or _default_identifier

    if _already_done('replace_bundle_id'):
        return
    warnings.warn('the NSBundle class is being monkeypatched %s' % (reason or ''))

    import ctypes
    C = ModuleProxy(['', 'c_'], [ctypes])

    capi = C.pythonapi

    # id objc_getClass(const char *name)
    capi.objc_getClass.restype = C.void_p
    capi.objc_getClass.argtypes = [C.char_p]

    # SEL sel_registerName(const char *str)
    capi.sel_registerName.restype = C.void_p
    capi.sel_registerName.argtypes = [C.char_p]

    def capi_get_selector(name):
        return C.void_p(capi.sel_registerName(name))

    # Method class_getInstanceMethod(Class aClass, SEL aSelector)
    # Will also search superclass for implementations.
    capi.class_getInstanceMethod.restype = C.void_p
    capi.class_getInstanceMethod.argtypes = [C.void_p, C.void_p]

    # void method_exchangeImplementations(Method m1, Method m2)
    capi.method_exchangeImplementations.restype = None
    capi.method_exchangeImplementations.argtypes = [C.void_p, C.void_p]

    class NSBundle(objc.Category(NS.Bundle)):

        @objc.typedSelector(NS.Bundle.bundleIdentifier.signature)
        def uitoolsBundleIdentifier(self):
            if self == NSBundle.mainBundle():
                return bundle_id
            return self.uitoolsBundleIdentifier()

    class_ = capi.objc_getClass("NSBundle")
    old_method = capi.class_getInstanceMethod(class_, capi_get_selector("bundleIdentifier"))
    new_method = capi.class_getInstanceMethod(class_, capi_get_selector("uitoolsBundleIdentifier"))
    capi.method_exchangeImplementations(old_method, new_method)


def initialize(standalone=False, fallback_indentifier=None):

    global _default_identifier

    if not _already_done('initialize'):
        app = NS.Application.sharedApplication()
        app.setDelegate_(WXAppDelegate.instance())

    if standalone:
        _standalone()

    if fallback_indentifier:
        _default_identifier = fallback_indentifier


def _standalone():

    if _already_done('initialize_standalone'):
        return
    initialize() # Yeah...

    app = NS.App
    # Thanks: http://www.cocoawithlove.com/2009/01/demystifying-nsapplication-by.html

    # Trigger applicationWillFinishLaunching (among others).
    app.finishLaunching()

    # TODO: Should we do this?
    #pool = NS.AutoreleasePool.alloc().init()

    # We trigger the app to listen for events, even though it doesn't seem
    # that an "event" is what triggers applicationDidFinishLaunching.
    # We just need to keep waiting for events long enough for that to happen.
    event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
        NS.AnyEventMask,
        NS.Date.dateWithTimeIntervalSinceNow_(0.1),
        NS.DefaultRunLoopMode,
        True
    )

    if event is not None:
        # This doesn't happen often, but lets give the event to the app
        # anyways (to be safe).
        app.sendEvent_(event)
        app.updateWindows()


def poll_event_loop(timeout=0):
    # We can either give an instanteous beforeDate and sleep ourselves,
    # or we can give it a positive time.
    run_loop = NS.RunLoop.currentRunLoop()
    until = NS.Date.dateWithTimeIntervalSinceNow_(timeout) # time from now in seconds
    run_loop.runMode_beforeDate_(NS.DefaultRunLoopMode, until)


def run_event_loop():
    NS.App.run()

