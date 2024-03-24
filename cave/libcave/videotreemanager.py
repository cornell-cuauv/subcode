from gi.repository import Gtk, Gdk, GLib
from misc.log import with_logging
from cave.libcave.video import Video
from cave.libcave.videofinder import VideoFinder

@with_logging
class VideoTreeManager:
    """
    Handles all video / log tree manipulations
    """

    def __init__(self, tree, parent):
        self.tree = tree
        self.parent = parent
        self.last_video_selected = None
        self.column_i = 1
        
        def add_column(title):
            cell = Gtk.CellRendererText()
            names = Gtk.TreeViewColumn(title, cell, markup=self.column_i)
            self.tree.append_column(names)
            self.column_i += 1

        add_column("Video File")

        self.treestore = Gtk.TreeStore(str)
        self.tree.set_model(self.treestore)

        self.videofinder = None

    def destroy(self):
        if self.videofinder is not None:
            self.videofinder.destroy()

    def on_select(self, tr_select):
        vid_select = self.get_selected_video()
        if vid_select is not None:
            self.switch_to_video(vid_select)

    def get_selection(self):
        item = self.tree.get_selection()
        if item is None:
            return None
        item = item.get_selected()[1]
        if item is None:
            return None
        obj_select = self.treestore.get_value(item, 0)
        return obj_select

    def switch_to_video(self, vid_select):
        if not vid_select.present():
            self.log.warning("Selected video not present")
            return

        if vid_select == self.last_video_selected:
            if vid_select is not None and isinstance(self.get_selection(), Video):
                # Selected already active video
                self.parent.timeline.set_length(self.parent.video_box.length)
                self.parent.set_frame_to(0)
            return
        self.last_video_selected = vid_select

        self.log.info("Selected video id %d" % vid_select.id)
        self.parent.video_box.load_video(vid_select)
        self.parent.timeline.set_length(self.parent.video_box.length)
        self.parent.logplayer.set_camera(vid_select.linked_camera)

        if vid_select.log_path:
            filename = Video.db.get_absolute_path(vid_select.log_path)
            self.parent.logplayer.set_log_file(filename)
    
    def get_selected_video(self):
        obj_selected = self.get_selection()
        if isinstance(obj_selected, Video):
            return obj_selected
        else:
            return None

    def missing_found(self, hash_to_video, done):
        for vhash, video_filename in hash_to_video.items():
            if video_filename is not None:
                # Update missing video paths if found
                self.missing_hashes[vhash].video_path = video_filename
                self.missing_hashes[vhash].update()
        if done:
            self.done_searching = True

        self.redraw()

    def redraw(self, filter_str=""):
        red_fmt = "<span background='red'>%s</span>"
        treestore = Gtk.TreeStore(object, str)
        vds = Video.get_all(filter_str)
        if self.videofinder is None:
            self.missing_hashes = {}
        for v in vds:
            if not v.present():
                if hasattr(v, "video_hash"):
                    if self.videofinder is None or not self.done_searching:
                        fmt = red_fmt % "%s [MISSING - Searching...]"
                        if self.videofinder is None:
                            self.missing_hashes[v.video_hash] = v
                    else:
                        fmt = red_fmt % "%s [MISSING - Not found.]"
                else:
                    self.log.warning("Video %s is missing but has no hash; won't search" % v)
                    fmt = red_fmt % "%s [MISSING - No Hash.]"
            else:
                fmt = "%s"

            treestore.append(None, (v, fmt % v.video_path))

        if self.videofinder is None and len(self.missing_hashes):
            self.videofinder = VideoFinder(self.parent.db.root_dir, self.missing_found)
            map(self.videofinder.request_search, self.missing_hashes.keys())
            self.done_searching = False
            self.videofinder.start()

        self.treestore = treestore
        self.tree.set_model(treestore)
        self.tree.expand_all()