# TODO:
# * Documentation -- this will need a new section of the User's Guide.
#      Both for Animations and just timers.
#   - Also need to update http://www.scipy.org/Cookbook/Matplotlib/Animations
# * Need to look at simplyfing iterator code through the use of:
#    iter(callable, sentinel) -> iterator
#    itertools.count()
#    anything else in itertools?
# * Blit
#   * Currently broken with Qt4 for widgets that don't start on screen
#   * Still a few edge cases that aren't working correctly
#   * Can this integrate better with existing matplotlib animation artist flag?
#   * Doesn't work with subplots example
# * Example
#   * Frameless animation - pure procedural with no loop
#   * Need example that uses something like inotify or subprocess
#   * Eric's complex syncing examples
# * Movies
#   * Library to make movies?
#   * RC parameter for config?
# * Need to consider event sources to allow clicking through multiple figures
from datetime import datetime

def traceme(func):
    def wrapper(*args):
        print '%s -- Calling: %s %s' % (datetime.now(), func.__name__, str(args))
        ret = func(*args)
        print 'Returned: %s' % func.__name__
        return ret
    return wrapper

#
# Start Backport of timers for older matplotlib
#

class TimerBase(object):
    '''
    A base class for providing timer events, useful for things animations.
    Backends need to implement a few specific methods in order to use their
    own timing mechanisms so that the timer events are integrated into their
    event loops.

    Mandatory functions that must be implemented:
    * _timer_start: Contains backend-specific code for starting the timer
    * _timer_stop: Contains backend-specific code for stopping the timer

    Optional overrides:
    * _timer_set_single_shot: Code for setting the timer to single shot
        operating mode, if supported by the timer object. If not, the Timer
        class itself will store the flag and the _on_timer method should
        be overridden to support such behavior.
    * _timer_set_interval: Code for setting the interval on the timer, if
        there is a method for doing so on the timer object.
    * _on_timer: This is the internal function that any timer object should
        call, which will handle the task of running all callbacks that have
        been set.

    Attributes:
    * interval: The time between timer events in milliseconds. Default
        is 1000 ms.
    * single_shot: Boolean flag indicating whether this timer should
        operate as single shot (run once and then stop). Defaults to False.
    * callbacks: Stores list of (func, args) tuples that will be called
        upon timer events. This list can be manipulated directly, or the
        functions add_callback and remove_callback can be used.
    '''
    def __init__(self, interval=None, callbacks=None):
        #Initialize empty callbacks list and setup default settings if necssary
        if callbacks is None:
            self.callbacks = []
        else:
            self.callbacks = callbacks[:] # Create a copy

        if interval is None:
            self._interval = 1000
        else:
            self._interval = interval

        self._single = False

        # Default attribute for holding the GUI-specific timer object
        self._timer = None

    def __del__(self):
        'Need to stop timer and possibly disconnect timer.'
        self._timer_stop()

    def start(self, interval=None):
        '''
        Start the timer object. `interval` is optional and will be used
        to reset the timer interval first if provided.
        '''
        if interval is not None:
            self.set_interval(interval)
        self._timer_start()

    def stop(self):
        '''
        Stop the timer.
        '''
        self._timer_stop()

    def _timer_start(self):
        #TODO: Could we potentially make a generic version through
        #the use of Threads?
        raise NotImplementedError('Needs to be implemented by subclass.')

    def _timer_stop(self):
        #TODO: Could we potentially make a generic version through
        #the use of Threads?
        raise NotImplementedError('Needs to be implemented by subclass.')

    def _get_interval(self):
        return self._interval

    def _set_interval(self, interval):
        self._interval = interval
        self._timer_set_interval()

    interval = property(_get_interval, _set_interval)

    def _get_single_shot(self):
        return self._single

    def _set_single_shot(self, ss=True):
        self._single = ss
        self._timer_set_single_shot()

    single_shot = property(_get_single_shot, _set_single_shot)

    def add_callback(self, func, *args, **kwargs):
        '''
        Register `func` to be called by timer when the event fires. Any
        additional arguments provided will be passed to `func`.
        '''
        self.callbacks.append((func, args, kwargs))

    def remove_callback(self, func, *args, **kwargs):
        '''
        Remove `func` from list of callbacks. `args` and `kwargs` are optional
        and used to distinguish between copies of the same function registered
        to be called with different arguments.
        '''
        if args or kwargs:
            self.callbacks.remove((func, args, kwargs))
        else:
            funcs = [c[0] for c in self.callbacks]
            if func in funcs:
                self.callbacks.pop(funcs.index(func))

    def _timer_set_interval(self):
        'Used to set interval on underlying timer object.'
        pass

    def _timer_set_single_shot(self):
        'Used to set single shot on underlying timer object.'
        pass

    def _on_timer(self):
        '''
        Runs all function that have been registered as callbacks. Functions
        can return False if they should not be called any more. If there
        are no callbacks, the timer is automatically stopped.
        '''
        for func,args,kwargs in self.callbacks:
            ret = func(*args, **kwargs)
            if ret == False:
                self.callbacks.remove((func,args,kwargs))

        if len(self.callbacks) == 0:
            self.stop()


class TimerQT(TimerBase):
    '''
    Subclass of :class:`backend_bases.TimerBase` that uses Qt4 timer events.

    Attributes:
    * interval: The time between timer events in milliseconds. Default
        is 1000 ms.
    * single_shot: Boolean flag indicating whether this timer should
        operate as single shot (run once and then stop). Defaults to False.
    * callbacks: Stores list of (func, args) tuples that will be called
        upon timer events. This list can be manipulated directly, or the
        functions add_callback and remove_callback can be used.
    '''
    def __init__(self, *args, **kwargs):
        TimerBase.__init__(self, *args, **kwargs)

        # Create a new timer and connect the timeout() signal to the
        # _on_timer method.
        from PyQt4 import QtCore
        self._timer = QtCore.QTimer()
        QtCore.QObject.connect(self._timer, QtCore.SIGNAL('timeout()'),
            self._on_timer)

    def __del__(self):
        # Probably not necessary in practice, but is good behavior to disconnect
        TimerBase.__del__(self)
        from PyQt4 import QtCore
        QtCore.QObject.disconnect(self._timer , QtCore.SIGNAL('timeout()'),
            self._on_timer)

    def _timer_set_single_shot(self):
        self._timer.setSingleShot(self._single)

    def _timer_set_interval(self):
        self._timer.setInterval(self._interval)

    def _timer_start(self):
        self._timer.start()

    def _timer_stop(self):
        self._timer.stop()


class TimerWx(TimerBase):
    '''
    Subclass of :class:`backend_bases.TimerBase` that uses WxTimer events.

    Attributes:
    * interval: The time between timer events in milliseconds. Default
        is 1000 ms.
    * single_shot: Boolean flag indicating whether this timer should
        operate as single shot (run once and then stop). Defaults to False.
    * callbacks: Stores list of (func, args) tuples that will be called
        upon timer events. This list can be manipulated directly, or the
        functions add_callback and remove_callback can be used.
    '''
    def __init__(self, parent, *args, **kwargs):
        TimerBase.__init__(self, *args, **kwargs)
        import wx
        # Create a new timer and connect the timer event to our handler.
        # For WX, the events have to use a widget for binding.
        self.parent = parent
        self._timer = wx.Timer(self.parent, wx.NewId())
        self.parent.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

     # Unbinding causes Wx to stop for some reason. Disabling for now.
#    def __del__(self):
#        import wx
#        TimerBase.__del__(self)
#        self.parent.Bind(wx.EVT_TIMER, None, self._timer)

    def _timer_start(self):
        self._timer.Start(self._interval, self._single)

    def _timer_stop(self):
        self._timer.Stop()

    def _timer_set_interval(self):
        self._timer_start()

    def _timer_set_single_shot(self):
        self._timer.start()

    def _on_timer(self, *args):
        TimerBase._on_timer(self)


class TimerTk(TimerBase):
    '''
    Subclass of :class:`backend_bases.TimerBase` that uses Tk's timer events.

    Attributes:
    * interval: The time between timer events in milliseconds. Default
        is 1000 ms.
    * single_shot: Boolean flag indicating whether this timer should
        operate as single shot (run once and then stop). Defaults to False.
    * callbacks: Stores list of (func, args) tuples that will be called
        upon timer events. This list can be manipulated directly, or the
        functions add_callback and remove_callback can be used.
    '''
    def __init__(self, parent, *args, **kwargs):
        TimerBase.__init__(self, *args, **kwargs)
        self.parent = parent

    def _timer_start(self):
        self._timer = self.parent.after(self._interval, self._on_timer)

    def _timer_stop(self):
        if self._timer is not None:
            self.parent.after_cancel(self._timer)
        self._timer = None

    def _on_timer(self):
        TimerBase._on_timer(self)

        # Tk after() is only a single shot, so we need to add code here to
        # reset the timer if we're not operating in single shot mode.
        if not self._single and len(self.callbacks) > 0:
            self._timer = self.parent.after(self._interval, self._on_timer)
        else:
            self._timer = None


class TimerGTK(TimerBase):
    '''
    Subclass of :class:`backend_bases.TimerBase` that uses GTK for timer events.

    Attributes:
    * interval: The time between timer events in milliseconds. Default
        is 1000 ms.
    * single_shot: Boolean flag indicating whether this timer should
        operate as single shot (run once and then stop). Defaults to False.
    * callbacks: Stores list of (func, args) tuples that will be called
        upon timer events. This list can be manipulated directly, or the
        functions add_callback and remove_callback can be used.
    '''
    def _timer_start(self):
        import gobject
        self._timer = gobject.timeout_add(self._interval, self._on_timer)

    def _timer_stop(self):
        import gobject
        if self._timer is not None:
            gobject.source_remove(self._timer)
            self._timer = None

    def _timer_set_interval(self):
        if self._timer is not None:
            self._timer_stop()
            self._timer_start()

    def _on_timer(self):
        TimerBase._on_timer(self)

        # Gtk timeout_add() requires that the callback returns True if it
        # is to be called again.
        if len(self.callbacks) > 0 and not self._single:
            return True
        else:
            self._timer = None
            return False


# Helper to monkey patch on timer methods and Null close events
# to earlier versions of matplotlib
def add_new_features(fig):
    # Do nothing if we already have new methods
    if hasattr(fig.canvas, 'new_timer'):
        return

    print 'Monkey patching canvas...'

    import matplotlib.pyplot as plt
    timers = dict(Qt4Agg=(TimerQT, None), WX=(TimerWx, lambda f: g.canvas),
        WXAgg=(TimerWx, lambda f: f.canvas), GTKAgg=(TimerGTK, None),
        GTK=(TimerGTK, None), TkAgg=(TimerTk, lambda f: f.canvas._tkcanvas))
    timer,parentFunc = timers[plt.get_backend()]

    if parentFunc:
        def f():
            return timer(parentFunc(fig))
    else:
        def f():
            return timer()
    fig.canvas.new_timer = f

    # Add the close_event signal so we don't get an error
    fig.canvas.callbacks.signals.add('close_event')
    fig.canvas.callbacks.callbacks['close_event'] = dict()

#
# End Backport of timers for older matplotlib
#
from matplotlib.cbook import iterable

class Animation(object):
    '''
    This class wraps the creation of an animation using matplotlib. It is
    only a base class which should be subclassed to provide needed behavior.

    *fig* is the figure object that is used to get draw, resize, and any
    other needed events.

    *event_source* is a class that can run a callback when desired events
    are generated, as well as be stopped and started. Examples include timers
    (see :class:`TimedAnimation`) and file system notifications.

    *blit* is a boolean that controls whether blitting is used to optimize
    drawing.
    '''
    def __init__(self, fig, event_source=None, blit=False):
        self._fig = fig
        self._blit = blit

        # These are the basics of the animation.  The frame sequence represents
        # information for each frame of the animation and depends on how the
        # drawing is handled by the subclasses. The event source fires events
        # that cause the frame sequence to be iterated.
        self.frame_seq = self.new_frame_seq()
        self.event_source = event_source

        # Clear the initial frame
        self._init_draw()

        # Instead of starting the event source now, we connect to the figure's
        # draw_event, so that we only start once the figure has been drawn.
        self._first_draw_id = fig.canvas.mpl_connect('draw_event', self._start)

        # Connect to the figure's close_event so that we don't continue to
        # fire events and try to draw to a deleted figure.
        self._close_id = self._fig.canvas.mpl_connect('close_event', self._stop)
        if blit:
            self._setup_blit()

    def _start(self, *args):
        '''
        Starts interactive animation. Adds the draw frame command to the GUI
        handler, calls show to start the event loop.
        '''
        # On start, we add our callback for stepping the animation and
        # actually start the event_source. We also disconnect _start
        # from the draw_events
        self.event_source.add_callback(self._step)
        self.event_source.start()
        self._fig.canvas.mpl_disconnect(self._first_draw_id)

    def _stop(self, *args):
        # On stop we disconnect all of our events.
        if self._blit:
            self._fig.canvas.mpl_disconnect(self._resize_id)
        self._fig.canvas.mpl_disconnect(self._close_id)
        self.event_source.remove_callback(self._step)
        self.event_source = None

    def save(self, filename, fps=5, codec='mpeg4', clear_temp=True,
        frame_prefix='_tmp'):
        '''
        Saves a movie file by drawing every frame.

        *fps* is the frames per second in the movie

        *codec* is the codec to be used,if it is supported by the output method.

        *clear_temp* specifies whether the temporary image files should be
        deleted.

        *frame_prefix* gives the prefix that should be used for individual
        image files.  This prefix will have a frame number (i.e. 0001) appended
        when saving individual frames.
        '''
        fnames = []
        # Create a new sequence of frames for saved data. This is different
        # from new_frame_seq() to give the ability to save 'live' generated
        # frame information to be saved later.
        for idx,data in enumerate(self.new_saved_frame_seq()):
            self._draw_next_frame(data, blit=False)
            fname = '%s%04d.png' % (frame_prefix, idx)
            fnames.append(fname)
            self._fig.savefig(fname)

        self._make_movie(filename, fps, codec, frame_prefix)

        #Delete temporary files
        if clear_temp:
            import os
            for fname in fnames:
                os.remove(fname)

    def ffmpeg_cmd(self, fname, fps, codec, frame_prefix):
        # Returns the command line parameters for subprocess to use
        # ffmpeg to create a movie
        return ['ffmpeg', '-y', '-r', str(fps), '-b', '1800k', '-i',
            '%s%%04d.png' % frame_prefix, fname]

    def mencoder_cmd(self, fname, fps, codec, frame_prefix):
        # Returns the command line parameters for subprocess to use
        # mencoder to create a movie
        return ['mencoder', 'mf://%s*.png' % frame_prefix, '-mf',
            'type=png:fps=%d' % fps, '-ovc', 'lavc', '-lavcopts',
            'vcodec=%s' % codec, '-oac', 'copy', '-o', fname]

    def _make_movie(self, fname, fps, codec, frame_prefix, cmd_gen=None):
        # Uses subprocess to call the program for assembling frames into a
        # movie file.  *cmd_gen* is a callable that generates the sequence
        # of command line arguments from a few configuration options.
        from subprocess import Popen, PIPE
        if cmd_gen is None:
            cmd_gen = self.ffmpeg_cmd
        proc = Popen(cmd_gen(fname, fps, codec, frame_prefix), shell=False,
            stdout=PIPE, stderr=PIPE)
        proc.wait()

    def _step(self, *args):
        '''
        Handler for getting events. By default, gets the next frame in the
        sequence and hands the data off to be drawn.
        '''
        # Returns True to indicate that the event source should continue to
        # call _step, until the frame sequence reaches the end of iteration,
        # at which point False will be returned.
        try:
            framedata = self.frame_seq.next()
            self._draw_next_frame(framedata, self._blit)
            return True
        except StopIteration:
            return False

    def new_frame_seq(self):
        'Creates a new sequence of frame information.'
        # Default implementation is just an iterator over self._framedata
        return iter(self._framedata)

    def new_saved_frame_seq(self):
        'Creates a new sequence of saved/cached frame information.'
        # Default is the same as the regular frame sequence
        return self.new_frame_seq()

    def _draw_next_frame(self, framedata, blit):
        # Breaks down the drawing of the next frame into steps of pre- and
        # post- draw, as well as the drawing of the frame itself.
        self._pre_draw(framedata, blit)
        self._draw_frame(framedata)
        self._post_draw(framedata, blit)

    def _init_draw(self):
        # Initial draw to clear the frame. Also used by the blitting code
        # when a clean base is required.
        pass

    def _pre_draw(self, framedata, blit):
        # Perform any cleaning or whatnot before the drawing of the frame.
        # This default implementation allows blit to clear the frame.
        if blit:
            self._blit_clear(self._drawn_artists, self._blit_cache)

    def _draw_frame(self, framedata):
        # Performs actual drawing of the frame.
        raise NotImplementedError('Needs to be implemented by subclasses to'
            ' actually make an animation.')

    def _post_draw(self, framedata, blit):
        # After the frame is rendered, this handles the actual flushing of
        # the draw, which can be a direct draw_idle() or make use of the
        # blitting.
        if blit and self._drawn_artists:
            self._blit_draw(self._drawn_artists, self._blit_cache)
        else:
            self._fig.canvas.draw_idle()

    # The rest of the code in this class is to facilitate easy blitting
    def _blit_draw(self, artists, bg_cache):
        # Handles blitted drawing, which renders only the artists given instead
        # of the entire figure.
        updated_ax = []
        for a in artists:
            # If we haven't cached the background for this axes object, do
            # so now. This might not always be reliable, but it's an attempt
            # to automate the process.
            if a.axes not in bg_cache:
                bg_cache[a.axes] = a.figure.canvas.copy_from_bbox(a.axes.bbox)
            a.axes.draw_artist(a)
            updated_ax.append(a.axes)

        # After rendering all the needed artists, blit each axes individually.
        for ax in set(updated_ax):
            ax.figure.canvas.blit(ax.bbox)

    def _blit_clear(self, artists, bg_cache):
        # Get a list of the axes that need clearing from the artists that
        # have been drawn. Grab the appropriate saved background from the
        # cache and restore.
        axes = set(a.axes for a in artists)
        for a in axes:
            a.figure.canvas.restore_region(bg_cache[a])

    def _setup_blit(self):
        # Setting up the blit requires: a cache of the background for the
        # axes
        self._blit_cache = dict()
        self._drawn_artists = []
        self._resize_id = self._fig.canvas.mpl_connect('resize_event',
            self._handle_resize)
        self._post_draw(None, self._blit)

    def _handle_resize(self, *args):
        # On resize, we need to disable the resize event handling so we don't
        # get too many events. Also stop the animation events, so that
        # we're paused. Reset the cache and re-init. Set up an event handler
        # to catch once the draw has actually taken place.
        self._fig.canvas.mpl_disconnect(self._resize_id)
        self.event_source.stop()
        self._blit_cache.clear()
        self._init_draw()
        self._resize_id = self._fig.canvas.mpl_connect('draw_event', self._end_redraw)

    def _end_redraw(self, evt):
        # Now that the redraw has happened, do the post draw flushing and
        # blit handling. Then re-enable all of the original events.
        self._post_draw(None, self._blit)
        self.event_source.start()
        self._fig.canvas.mpl_disconnect(self._resize_id)
        self._resize_id = self._fig.canvas.mpl_connect('resize_event',
            self._handle_resize)


class TimedAnimation(Animation):
    '''
    :class:`Animation` subclass that supports time-based animation, drawing
    a new frame every *interval* milliseconds.

    *repeat* controls whether the animation should repeat when the sequence
    of frames is completed.

    *repeat_delay* optionally adds a delay in milliseconds before repeating
    the animation.
    '''
    def __init__(self, fig, interval=200, repeat_delay=None, repeat=True,
            event_source=None, *args, **kwargs):
        # Store the timing information
        self._interval = interval
        self._repeat_delay = repeat_delay
        self.repeat = repeat

        # If we're not given an event source, create a new timer. This permits
        # sharing timers between animation objects for syncing animations.
        if event_source is None:
            event_source = fig.canvas.new_timer()
            event_source.interval = self._interval

        Animation.__init__(self, fig, event_source=event_source, *args, **kwargs)

    def _step(self, *args):
        '''
        Handler for getting events.
        '''
        # Extends the _step() method for the Animation class.  If
        # Animation._step signals that it reached the end and we want to repeat,
        # we refresh the frame sequence and return True. If _repeat_delay is
        # set, change the event_source's interval to our loop delay and set the
        # callback to one which will then set the interval back.
        still_going = Animation._step(self, *args)
        if not still_going and self.repeat:
            if self._repeat_delay:
                self.event_source.remove_callback(self._step)
                self.event_source.interval = self._repeat_delay
                self.event_source.add_callback(self._loop_delay)
            self.frame_seq = self.new_frame_seq()
            return True
        else:
            return still_going

    def _stop(self, *args):
        # If we stop in the middle of a loop delay (which is relatively likely
        # given the potential pause here, remove the loop_delay callback as
        # well.
        self.event_source.remove_callback(self._loop_delay)
        Animation._stop(self)

    def _loop_delay(self, *args):
        # Reset the interval and change callbacks after the delay.
        self.event_source.remove_callback(self._loop_delay)
        self.event_source.interval = self._interval
        self.event_source.add_callback(self._step)


class ArtistAnimation(TimedAnimation):
    '''
    Before calling this function, all plotting should have taken place
    and the relevant artists saved.

    frame_info is a list, with each list entry a collection of artists that
    represent what needs to be enabled on each frame. These will be disabled
    for other frames.
    '''
    def __init__(self, fig, artists, *args, **kwargs):
        # Internal list of artists drawn in the most recent frame.
        self._drawn_artists = []

        # Use the list of artists as the framedata, which will be iterated
        # over by the machinery.
        self._framedata = artists
        TimedAnimation.__init__(self, fig, *args, **kwargs)

    def _init_draw(self):
        # Make all the artists involved in *any* frame invisible
        axes = []
        for f in self.new_frame_seq():
            for artist in f:
                artist.set_visible(False)
                # Assemble a list of unique axes that need flushing
                if artist.axes not in axes:
                    axes.append(artist.axes)

        # Flush the needed axes
        for ax in axes:
            ax.figure.canvas.draw()

    def _pre_draw(self, framedata, blit):
        '''
        Clears artists from the last frame.
        '''
        if blit:
            # Let blit handle clearing
            self._blit_clear(self._drawn_artists, self._blit_cache)
        else:
            # Otherwise, make all the artists from the previous frame invisible
            for artist in self._drawn_artists:
                artist.set_visible(False)

    def _draw_frame(self, artists):
        # Save the artists that were passed in as framedata for the other
        # steps (esp. blitting) to use.
        self._drawn_artists = artists

        # Make all the artists from the current frame visible
        for artist in artists:
            artist.set_visible(True)

# Do nothing generator for use in procedural animations that live-generate
# data.
def null_generator():
    while True: yield 0

class FuncAnimation(TimedAnimation):
    '''
    Makes an animation by repeatedly calling a function *func*, passing in
    (optional) arguments in *fargs*.

    *frames* can be a generator, an iterable, or a number of frames.

    *init_func* is a function used to draw a clear frame. If not given, the
    results of drawing from the first item in the frames sequence will be
    used.
    '''
    def __init__(self, fig, func, frames=None ,init_func=None, fargs=None,
            **kwargs):
        if fargs:
            self._args = fargs
        else:
            self._args = ()
        self._func = func

        # Set up a function that creates a new iterable when needed. If nothing
        # is passed in for frames, just use the null_generator. A callable
        # passed in for frames is assumed to be a generator. An iterable will
        # be used as is, and anything else will be treated as a number of
        # frames.
        if frames is None:
            self._iter_gen = null_generator
        elif callable(frames):
            self._iter_gen = frames
        elif iterable(frames):
            self._iter_gen = lambda: iter(frames)
        else:
            self._iter_gen = lambda: iter(range(frames))

        self._init_func = init_func
        self._save_seq = []

        TimedAnimation.__init__(self, fig, **kwargs)

    def new_frame_seq(self):
        # Use the generating function to generate a new frame sequence
        return self._iter_gen()

    def new_saved_frame_seq(self):
        # Generate an iterator for the sequence of saved data.
        return iter(self._save_seq)

    def _init_draw(self):
        # Initialize the drawing either using the given init_func or by
        # calling the draw function with the first item of the frame sequence.
        # For blitting, the init_func should return a sequence of modified
        # artists.
        if self._init_func is None:
            self._draw_frame(self.new_frame_seq().next())
        else:
            self._drawn_artists = self._init_func()

    def _draw_frame(self, framedata):
        # Save the data for potential saving of movies.
        self._save_seq.append(framedata)

        # Call the func with framedata and args. If blitting is desired,
        # func needs to return a sequence of any artists that were modified.
        self._drawn_artists = self._func(framedata, *self._args)

if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt

    def update_line(num, data, line):
        line.set_data(data[...,:num])
        return line,

    fig1 = plt.figure()

    # add_new_timer only needed while running old matplotlib. This will dissappear
    # and no longer be necessary.
    if not hasattr(fig1.canvas, 'new_timer'): add_new_features(fig1)

    data = np.random.rand(2, 25)
    l, = plt.plot([], [], 'r-')
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.xlabel('x')
    plt.title('test')
    line_ani = FuncAnimation(fig1, update_line, 25, fargs=(data, l), interval=50, blit=True)
#    line_ani.save('lines.mp4')

    fig2 = plt.figure()

    # add_new_timer only needed while running old matplotlib. This will dissappear
    # and no longer be necessary.
    if not hasattr(fig2.canvas, 'new_timer'): add_new_features(fig2)

    x = np.arange(-9, 10)
    y = np.arange(-9, 10).reshape(-1, 1)
    base = np.hypot(x, y)
    ims = []
    for add in np.arange(15):
        ims.append((plt.pcolor(x, y, base + add, norm=plt.Normalize(0, 30)),))
    im_ani = ArtistAnimation(fig2, ims, interval=50, repeat_delay=1000, blit=False)
#    im_ani.save('im.mp4')

    plt.show()
