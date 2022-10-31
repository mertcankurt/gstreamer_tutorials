#!/usr/bin/env python3
import sys, os
from loguru import logger
from dataclasses import dataclass, field
from pathlib import Path

try:
    import gi
except Exception as msg:
    logger.error("'gi' module can not be found quiting program!!!")
    sys.exit(-99)
else:
    gi.require_version("Gst", "1.0")

    from gi.repository import Gst


@dataclass(order=True)
class GstClass:
    terminate: bool = False
    pipeline: Gst.Element = field(init=False)
    source: Gst.Element = field(init=False)
    audio_convert: Gst.Element = field(init=False)
    audio_resample: Gst.Element = field(init=False)
    audio_sink: Gst.Element = field(init=False)
    video_convert: Gst.Element = field(init=False)
    video_sink: Gst.Element = field(init=False)

    def __post_init__(self):
        # Initialize GStreamer
        Gst.init(sys.argv[1:])

        # Create the elements
        self.source = Gst.ElementFactory.make("uridecodebin", "source")
        self.audio_convert = Gst.ElementFactory.make("audioconvert", "audio_convert")
        self.audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
        self.audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")
        self.video_convert = Gst.ElementFactory.make("videoconvert", "video_convert")
        self.video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")

        # Create an empty pipeline
        self.pipeline = Gst.Pipeline.new("test-pipeline")

        if (
            not self.pipeline
            or not self.source
            or not self.audio_convert
            or not self.audio_resample
            or not self.audio_sink
            or not self.video_convert
            or not self.video_sink
        ):
            logger.error("Not all elements could be created.")
            sys.exit(1)

        # Build the pipeline. Note that we are NOT linking the source at this point.
        # We will do it later.
        self.pipeline.add(self.source, self.audio_convert, self.audio_resample, self.audio_sink, self.video_convert, self.video_sink)
        if not self.audio_convert.link(self.audio_resample) or not self.audio_resample.link(self.audio_sink) or not self.video_convert.link(self.video_sink):
            logger.error("Elements could not be linked.")
            sys.exit(1)

        # Set the URI to play
        video_file_pth = Path(os.path.abspath("./sample_videos/sample_video1.mp4")).as_uri()
        self.source.set_property("uri", video_file_pth)
        # Connect to the pad-added signal
        self.source.connect("pad-added", self.on_pad_added)
        # Start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        bus = self.pipeline.get_bus()
        while not self.terminate:
            msg = bus.timed_pop_filtered(
                Gst.CLOCK_TIME_NONE,
                Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS,
            )
            self.handle_message(msg)

        # free resources
        self.pipeline.set_state(Gst.State.NULL)

    # handler for the pad-added signal
    def on_pad_added(self, src, new_pad):
        # check the new pad's type
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        print(f"Received new pad '{new_pad.get_name()}' from '{src.get_name()}', padtype: '{new_pad_type}'")

        if new_pad_type.startswith("audio/x-raw"):
            sink_pad = self.audio_convert.get_static_pad("sink")
        elif new_pad_type.startswith("video/x-raw"):
            sink_pad = self.video_convert.get_static_pad("sink")
        else:
            print(f"It has type '{new_pad_type}' which is not raw audio/video. Ignoring.")
            return

        # if our converter is already linked, we have nothing to do here
        if sink_pad.is_linked():
            print("We are already linked. Ignoring.")
            return

        # attempt the link
        ret = new_pad.link(sink_pad)
        if not ret == Gst.PadLinkReturn.OK:
            print(f"Type is '{new_pad_type}' but link failed")
        else:
            print(f"Link succeeded (type '{new_pad_type}')")

        return

    def handle_message(self, msg):
        # Parse Message
        if not msg:
            return

        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print("ERROR:", msg.src.get_name(), " ", err.message)
            if dbg:
                print("debugging info: ", dbg)
            self.terminate = True
        elif t == Gst.MessageType.EOS:
            print("End-Of-Stream reached")
            self.terminate = True
        elif t == Gst.MessageType.STATE_CHANGED:
            # We are only interested in STATE_CHANGED messages from the pipeline
            if msg.src == self.pipeline:
                old_state, new_state, pending_state = msg.parse_state_changed()
                print(f"Pipeline state changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}")
        else:
            # should not get here
            print("ERROR: Unexpected message received")
            self.terminate = True


if __name__ == "__main__":
    streamer = GstClass()
