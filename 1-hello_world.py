#!/usr/bin/env python3
import sys, os, gi
from pathlib import Path

gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gst, GObject, GLib

pipeline = None
bus = None
message = None

# initialize GStreamer
Gst.init(sys.argv[1:])

# build the pipeline
video_file_pth = Path(os.path.abspath("./sample_videos/sample_video1.mp4")).as_uri()
pipeline = Gst.parse_launch(f"playbin uri={video_file_pth}")

# start playing
pipeline.set_state(Gst.State.PLAYING)

# wait until EOS or error
bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

# free resources
pipeline.set_state(Gst.State.NULL)
