#!/usr/bin/env python3
import sys, os
from loguru import logger
from dataclasses import dataclass, field
from pathlib import Path
from numpy import int64
from helper import format_ns

try:
    import gi
except Exception as msg:
    logger.error("'gi' module can not be found quiting program!!!")
    sys.exit(-99)
else:
    gi.require_version("Gst", "1.0")

    from gi.repository import Gst


@dataclass(order=True)
class VideoPlayer:
    playbin: Gst.Element = field(init=False)  # Our one and only element
    playing: bool = False  # are we playing?
    terminate: bool = False  # should we terminate execution?
    seek_enabled: bool = False  # is seeking enabled for this media?
    seek_done: bool = False  # have we performed the seek already?
    duration: int64 = Gst.CLOCK_TIME_NONE  # media duration (ns)

    def __post_init__(self):
        # Initialize GStreamer
        Gst.init(sys.argv[1:])

        # Create the elements
        self.playbin = Gst.ElementFactory.make("playbin", "playbin")

        if not self.playbin:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        # set uri to play
        video_file_pth = Path(os.path.abspath("./sample_videos/sample_video1.mp4")).as_uri()
        self.playbin.set_property("uri", video_file_pth)

    def play(self):
        # Start playing
        ret = self.playbin.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)
        try:
            bus = self.playbin.get_bus()
            while not self.terminate:
                msg = bus.timed_pop_filtered(
                    100 * Gst.MSECOND,
                    Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.DURATION_CHANGED,
                )

                # parse message
                if msg:
                    self.handle_message(msg)
                else:
                    # we got no message. this means the timeout expired
                    if self.playing:
                        current = -1
                        # query the current position of the stream
                        ret, current = self.playbin.query_position(Gst.Format.TIME)
                        if not ret:
                            print("ERROR: Could not query current position")

                        # if we don't know it yet, query the stream duration
                        if self.duration == Gst.CLOCK_TIME_NONE:
                            (ret, self.duration) = self.playbin.query_duration(Gst.Format.TIME)
                            if not ret:
                                print("ERROR: Could not query stream duration")

                        # print current position and total duration
                        print(f"Position {format_ns(current)} / {format_ns(self.duration)}")

                        # if seeking is enabled, we have not done it yet and the time is right,
                        # seek
                        if self.seek_enabled and not self.seek_done and current > 10 * Gst.SECOND:
                            print("Reached 10s, performing seek...")
                            self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 30 * Gst.SECOND)
                            self.seek_done = True
        finally:
            self.playbin.set_state(Gst.State.NULL)

    def handle_message(self, msg):
        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print("ERROR:", msg.src.get_name(), ":", err)
            if dbg:
                print("Debug info:", dbg)
            self.terminate = True
        elif t == Gst.MessageType.EOS:
            print("End-Of-Stream reached")
            self.terminate = True
        elif t == Gst.MessageType.DURATION_CHANGED:
            # the duration has changed, invalidate the current one
            self.duration = Gst.CLOCK_TIME_NONE
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = msg.parse_state_changed()
            if msg.src == self.playbin:
                print(f"Pipeline state changed from '{Gst.Element.state_get_name(old_state)}' to '{Gst.Element.state_get_name(new_state)}'")

                # remember whether we are in the playing state or not
                self.playing = new_state == Gst.State.PLAYING

                if self.playing:
                    # we just moved to the playing state
                    query = Gst.Query.new_seeking(Gst.Format.TIME)
                    if self.playbin.query(query):
                        fmt, self.seek_enabled, start, end = query.parse_seeking()

                        if self.seek_enabled:
                            print(f"Seeking is ENABLED (from {format_ns(start)} to {format_ns(end)})")
                        else:
                            print("Seeking is DISABLED for this stream")
                    else:
                        print("ERROR: Seeking query failed")

        else:
            print("ERROR: Unexpected message received")


if __name__ == "__main__":
    player = VideoPlayer()
    player.play()
