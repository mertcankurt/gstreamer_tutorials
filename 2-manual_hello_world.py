#!/usr/bin/env python3
import sys
from loguru import logger
from dataclasses import dataclass, field

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
    pipeline: Gst.Element = field(init=False)
    source: Gst.Element = field(init=False)
    convert: Gst.Element = field(init=False)
    resample: Gst.Element = field(init=False)
    sink: Gst.Element = field(init=False)

    def __post_init__(self):
        # Initialize GStreamer
        Gst.init(sys.argv[1:])

        # Create the elements
        self.source = Gst.ElementFactory.make("videotestsrc", "source")
        self.filter = Gst.ElementFactory.make("vertigotv", "filter")
        self.convert = Gst.ElementFactory.make("videoconvert", "convert")
        self.sink = Gst.ElementFactory.make("autovideosink", "sink")

        # Create the empty pipeline
        self.pipeline = Gst.Pipeline.new("test-pipeline")

        if not self.pipeline or not self.source or not self.convert or not self.sink:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        # Build the pipeline
        self.pipeline.add(self.source, self.filter, self.convert, self.sink)
        if not self.source.link(self.filter) or not self.filter.link(self.convert) or not self.convert.link(self.sink):
            logger.error("Elements could not be linked.")
            sys.exit(1)

        # Modify the source's properties
        self.source.props.pattern = 0
        # Can alternatively be done using `source.set_property("pattern",0)`
        # or using `Gst.util_set_object_arg(source, "pattern", 0)`

        # Start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        # Wait for EOS or error
        bus = self.pipeline.get_bus()
        msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

        self.handle_message(msg)

        self.pipeline.set_state(Gst.State.NULL)

    def handle_message(self, msg):
        # Parse message
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
                logger.error(f"Debugging information: {debug_info if debug_info else 'none'}")
            elif msg.type == Gst.MessageType.EOS:
                logger.info("End-Of-Stream reached.")
            else:
                # This should not happen as we only asked for ERRORs and EOS
                logger.error("Unexpected message received.")


if __name__ == "__main__":
    streamer = GstClass()
