#!/usr/bin/env python3

import os, signal, sys, json
import logging

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib

import argparse
import math

from cave.addvideo import AddVideo
from cave.adddb import AddDatabase
from cave.newdbname import AddDatabaseName
from cave.editvideo import EditVideo
from cave.testwindow import TestWindow
from cave.gui.filepicker import FilePicker, FileTypes
from cave.libcave.database import Database
from cave.statusbarmanager import StatusBarManager
from misc.log import init_logging, with_logging
from cave.libcave.videotreemanager import VideoTreeManager
from cave.libcave.dbtreemanager import DatabaseTreeManager
from cave.libcave.video import Video
from cave.timeline import Timeline
from cave.videobox import VideoBox
from cave.videoplayer import VideoPlayer
from cave.logplayer import LogPlayer
from cave.libcave.cameralink import CameraLink
from cave.videopreviewmanager import VideoPreviewManager
from cave.libcave.videoutils import hash_video

from misc.utils import register_exit_signals

__location__ = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0])))

ap = argparse.ArgumentParser(description='CUAUV Automated Vision Evaluator: A program for video ' +
        'database management and automated vision testing')
ap.add_argument('database', type=str, default="", nargs='?', help='filename of the database to load (optional)')
ap.add_argument('--filter', type=str, default="", help='filename of the config file   \
        containing variables to play back (filter config files take the same format   \
        as shared memory config files; simply copy vars.conf and remove all unwanted  \
        variables)')

args = ap.parse_args()


@with_logging
class Cave:
    """
    Main GUI for the CAVE app"
    """

    config_file = "~/.cave"

    def window_destroy(self, event):
        # Close this application
        self.logger.critical("Program shutdown!")
        self.statusbar.destroy()
        self.video_tree_manager.destroy()
        self.video_preview_manager.destroy()
        self.video_box.kill_thread()
        self.video_player.destroy()
        self.logplayer.destroy()
        Gtk.main_quit()

        if self.db is not None:
            try:
                f = open(os.path.expanduser(self.config_file), "w")
            except:
                self.logger.warning("Unable to save configuration in %s" % \
                                    self.config_file)
            else:
                #Config files
                f.write("%s" % self.db.get_filename())
                f.close()

    def db_add(self, event):
        """
        Invoked when +DB is clicked.
        Adds a database to the list of loaded directories.
        """

        self.logger.info("Database add clicked")
        ad = AddDatabase(self.db_add_callback, default_folder=self.db.root_dir)
        pass

    def db_add_callback(self, ad):
        """
        Invoked when OK is selected after the AddDatabase file.
        Adds a database to the directory.
        """
        self.logger.info("Database add callback invoked")

        json_file_path = self.database_tree_manager.database_json_path

        # Add database to the records
        self.database_tree_manager.records[ad.db_name] = ad.db_filename
        with open(json_file_path, 'w') as file:
            json.dump(self.database_tree_manager.records, file, indent=2)
        self.database_tree_manager.redraw()

    def db_remove(self, event):
        """
        Invoked when -DB is clicked.
        Removes a database to the list of loaded directories.
        """

        self.logger.info("Database remove clicked")

        db_select = self.database_tree_manager.get_selection(get_name=True)
        if db_select is None:
            self.logger.error("Removal failed. No video was selected.")
            self.statusbar.display("No video selected", 3)
        else:
            self.database_tree_manager.records.pop(db_select)
            json_file_path = self.database_tree_manager.database_json_path
            with open(json_file_path, 'w') as file:
                json.dump(self.database_tree_manager.records, file, indent=2)
            self.database_tree_manager.redraw()
        pass

    def database_add(self, event):
        """
        Invoked when +Video is clicked.
        Adds a video to the currently selected database.
        """

        #Launch DB add window
        self.logger.debug("Database add clicked")
        if self.db is None:
            self.logger.error("A database must be opened to add a video.")
            self.statusbar.display("Open a database first.", 3)
            return

        av = AddVideo(self.database_add_callback, default_folder=self.db.root_dir)

    #Add Video callback; compute paths and add video to database
    def database_add_callback(self, av):
        """
        Invoked when OK is selected after the AddVideo file.
        Adds a video to the currently selected database.
        """

        self.logger.debug("Callback executed")

        if av.log_filename is None:
            log_path = ""
        else:
            log_path = self.db.get_relative_path(av.log_filename)

        vid_path = self.db.get_relative_path(av.video_filename)
        if vid_path is None:
            return

        self.logger.info("Hashing video \"%s\"..." % av.video_filename)

        vid = Video.new(name=av.video_name, video_path=vid_path, log_path=log_path, linked_camera=av.linked_camera, meta=av.meta, video_hash=hash_video(av.video_filename))
        self.logger.info("Added video \"%s\" to database (id #%d)" % (vid.name, vid.id))
        self.statusbar.display("Added video \"%s\"" % vid.name, 3)
        self.video_tree_manager.redraw()

    #Load the database from a given path
    def load_db(self, path):
        if path is None:
            return
        self.db = Database(path)
        if self.db is not None and self.db.error:
            self.log.error("Failed to load database %s" % path)
            self.db = None
            return

        if self.db is not None and path is not None:
            path = os.path.abspath(path)
            self.db_label = self.builder.get_object("databaseLabel")
            self.db_label.set_text(os.path.basename(path))
            self.window.set_title("CAVE -- %s" % os.path.basename(path))
            self.statusbar.display("Opened database %s" % path, 3)
            self.logger.info("Opened database %s" % os.path.basename(path))
            self.video_tree_manager.redraw()

            #Enable all operations

    def video_remove(self, event):
        #Remove selected video from the database
        vid_select = self.video_tree_manager.get_selected_video()
        if vid_select is None:
            self.logger.error("Removal failed. No video was selected.")
            self.statusbar.display("No video selected", 3)
        else:
            vid_select.remove()
            self.video_tree_manager.redraw()
            self.logger.info("Removed video \"%s\" from the database." % vid_select.name)
            self.statusbar.display("Removed video \"%s\"" % vid_select.name, 3)

    def database_open(self, event):
        self.load_db(FilePicker.open(title="Open an existing CAVE database", type_list=[FileTypes.CDB]))

    def database_new(self, event):
        path = FilePicker.new(title="Select a location to save a new cave database", default_filename="database.cdb", type_list=[FileTypes.CDB])
        self.load_db(path)
        if path is not None:
            adn = AddDatabaseName(self.dummy, path=path, default_folder=self.db.root_dir)
        
    # THIS IS SO JANK
    def dummy(self, av):
        print("-----")
        print(av)

        # Add database to the records
        name = av.db_name
        self.database_tree_manager.records[name] = av.path
        json_file_path = self.database_tree_manager.database_json_path
        with open(json_file_path, 'w') as file:
            json.dump(self.database_tree_manager.records, file, indent=2)
        self.database_tree_manager.redraw()
        pass

    def videotree_selected(self, vt):
        if self.init:
            self.video_tree_manager.on_select(vt)
            self.timeline.enabled = True

    def databasetree_selected(self, vt):
        if self.init:
            self.database_tree_manager.on_select(vt)
            v = self.database_tree_manager.get_selection()
            self.load_db(v)
            # print(v)
            

    def play_button_toggled(self, vt):
        if self.manual_play_reset:
            self.manual_play_reset = False
            return

        vid_select = self.video_tree_manager.get_selected_video()
        if vid_select is None:
            self.logger.error("Video playing failed. No video was selected.")
            self.statusbar.display("No video selected", 3)
            self.manual_play_reset = True
            self.play_button.set_active(not self.play_button.get_active())
        else:
            self.video_player.set_play(self.builder.get_object("exportCheck").get_active(), self.play_button.get_active())

    def loop_button_toggled(self, event):
        self.timeline.set_loop_enabled(self.loop_button.get_active())

    def frames_to_vision_checked(self, event):
        button = self.builder.get_object("exportCheck")
        self.video_box.export_to_vision(button.get_active())
        if self.video_tree_manager.get_selected_video() is not None:
            self.video_player.set_play(self.builder.get_object("exportCheck").get_active(), self.play_button.get_active())

    def frames_to_log_checked(self, event):
        button = self.builder.get_object("logCheck")
        self.logplayer.set_enabled(button.get_active())

    def full_screen_checked(self, event):
        button = self.builder.get_object("fullScreenCheck")
        settings = self.builder.get_object("settingsBox")
        panel = self.builder.get_object("panelBox")
        if button.get_active():
            self.log.info('Activating compact mode.')
            settings.hide()
            panel.hide()
        else:
            self.log.info('Disabling compact mode.')
            settings.show()
            panel.show()

    def enable_video_previews(self, event):
        button = self.builder.get_object("previewCheck")
        self.video_preview_manager.set_enabled(button.get_active())
        self.timeline.queue_draw()

    def edit_video(self, event):
        self.logger.debug("Edit video clicked")

        vid_select = self.video_tree_manager.get_selected_video()
        if vid_select is None:
            self.logger.error("Edit of video failed. No video was selected.")
            self.statusbar.display("No video selected", 3)
        else:
            ev = EditVideo(self.edit_video_callback, vid_select)

    def edit_video_callback(self, av):
        if av.log_filename is None:
            log_path = ""
        else:
            log_path = self.db.get_relative_path(av.log_filename)

        vid_path = self.db.get_relative_path(av.video_filename)
        if vid_path is None:
            return

        av.video.name = av.video_name
        av.video.video_path = vid_path
        av.video.log_path = log_path
        av.video.linked_camera = av.linked_camera
        av.video.meta = av.meta

        av.video.update()
        self.video_tree_manager.redraw()

    #Steps the frame count
    def increment_frame(self, count):
        new_frame = self.timeline.cursor + count
        self.set_frame_to(new_frame)

    def set_frame_to(self, new_frame):
        if new_frame >= 0 and new_frame < self.timeline.length:
            self.timeline.move_cursor(new_frame)
            self._change_frame(new_frame)

    #Steps the frame count but replays video when it hits the end
    def increment_frame_loop(self, count):
        loop_start, loop_end = self.timeline.get_loop_bounds()
        end_frame = self.timeline.length-1 if math.isnan(loop_end) else loop_end
        next_frame = self.timeline.cursor + count
        increment = next_frame >= loop_start and next_frame <= end_frame
        if not increment:
            next_frame = loop_start
        self.timeline.move_cursor(next_frame)
        self._change_frame(next_frame)

    def launch_test_window(self, event):
        self.log.info("Launching test window")
        TestWindow(self)

    def video_filter(self, event):
        filter_str = self.filter_box.get_text()
        tokens = filter_str.split()

        if len(tokens) > 0:
            query = "WHERE "
            tokenquery = "meta LIKE '%%%s%%'"
            for token in tokens[:len(tokens)-1]:
                query += tokenquery % token + " AND "
            query += tokenquery % tokens[-1]
        else:
            query = ""

        self.video_tree_manager.redraw(query)

    def _change_frame(self, frame):
        #Sets the videobox and logplayer frame
        self.video_box.set_frame(frame)
        self.logplayer.set_frame(frame)

    def __init__(self):
        self.init = False
        self.gladefile = os.path.join(__location__, "gui/cave.glade")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)

        # Automatically connect signals to functions defined above
        self.builder.connect_signals(self)

        #Set up the video tree
        self.video_tree = self.builder.get_object("videoTreeView")
        self.video_tree_manager = VideoTreeManager(self.video_tree, self)

        #Set up the filter box
        self.filter_box = self.builder.get_object("filterEntry")

        # Set up the database
        self.database_tree = self.builder.get_object("databaseTreeView")
        self.database_tree_manager = DatabaseTreeManager(self.database_tree, self)
        self.database_tree_manager.redraw()

        #Create & link video display widget
        self.video_box_container = self.builder.get_object("videoBox")
        self.video_box = VideoBox(self)
        self.video_box.show()
        self.video_box_container.pack_start(self.video_box, True, True, 0)

        #Create & Link timeline widget
        self.timeline_box = self.builder.get_object("timelineBox")
        self.timeline = Timeline(self)
        self.timeline.show()
        self.timeline_box.pack_start(self.timeline, True, True, 0)

        self.timeline.cursor_change = self._change_frame #Register listener

        self.video_box.length_listener = self.timeline.set_length #Register listener

        #Log playback
        filter_file = os.path.expanduser(args.filter) if args.filter else ''
        self.logplayer = LogPlayer(filter=filter_file)

        # Get the main window
        self.window = self.builder.get_object("caveWindow")
        self.window.show()

        #Initialize gtk's thread engine; add any threads after these lines
        Gdk.threads_init()
        GLib.threads_init()

        #Start video player thread
        self.video_player = VideoPlayer(self)
        self.play_button = self.builder.get_object("playButton")
        # Used to ignore program play button toggling.
        self.manual_play_reset = False

        self.enable_button = self.builder.get_object("enableButton")
        self.toggle_all_button = self.builder.get_object("toggleAllButton")

        #Start video rendering thread
        self.video_box.start_thread()

        #Start video preview manager
        self.video_preview_manager = VideoPreviewManager(self.video_box.vmt) #link w/ video manager thread
        self.video_preview_manager.register_callback(self.timeline.preview_callback)
        self.timeline.set_preview_manager(self.video_preview_manager)

        #Create statusbar display thread
        self.statusbar = StatusBarManager(self.builder.get_object("statusBar"))
        self.statusbar.display("Welcome to CAVE!", 2)

        self.db = None

        self.loop_button = self.builder.get_object("loopButton")

        #Load database file from arguments if present
        if args.database:
            self.load_db(args.database)
        elif os.path.exists(os.path.expanduser(self.config_file)):
            #Config File
            f = open(os.path.expanduser(self.config_file), "r")
            self.load_db(f.read())
        else:
            vision_test_path = 'VISION_TEST_PATH'
            if vision_test_path in os.environ:
                #Search for databases in $VISION_TEST_PATH
                test_path = os.path.expandvars(os.path.expanduser(os.environ[vision_test_path]))
                for f in os.listdir(test_path):
                    fname = os.path.join(test_path, f)
                    if os.path.isfile(fname) and fname.endswith('.cdb'):
                        self.load_db(fname)
                        break

        #Ctrl+C handling
        def handler(signum, frame):
            self.log.warning("INTERRUPT; stopping CAVE")
            self.window_destroy(None)
        register_exit_signals(handler)

        #This fairly pointless function is necessary to periodically wake up
        #the gtk main thread to detect system interrupts even when not focused
        #I believe this is due to a Gtk bug
        GLib.timeout_add(500, lambda : True)

        #Make the window more shrinkable
        self.window.set_size_request(400,400)

        #Fire up the main window
        self.log.info("Launching GUI. Welcome to CAVE!")
        self.init = True
        Gdk.threads_enter()
        Gtk.main()
        Gdk.threads_leave()

if __name__ == "__main__":
    #Create an instance of the GTK app and run it
    init_logging(log_level = logging.DEBUG)
    main = Cave()
