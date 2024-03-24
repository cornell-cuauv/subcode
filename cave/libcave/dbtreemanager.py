from gi.repository import Gtk, Gdk, GLib
from misc.log import with_logging
from cave.libcave.database import Database
from cave.libcave.videofinder import VideoFinder
import json
import os

JSON_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "databases.json")

@with_logging
class DatabaseTreeManager:
    """
    Handles all database tree manipulations
    """

    def __init__(self, tree, parent):
        self.database_json_path = JSON_FILE
        self.tree = tree
        self.parent = parent
        self.last_video_selected = None
        self.records = self.load_records()
        self.column_i = 0

        def add_column(title, column_index, spacing=10):
            cell = Gtk.CellRendererText()
            names = Gtk.TreeViewColumn(title, cell, text=column_index)
            names.set_spacing(spacing)
            self.tree.append_column(names)

        # Add columns to the TreeView
        add_column("Name", 0, spacing=20)
        add_column("File", 1, spacing=20)

        # Set up the TreeStore with two columns
        self.treestore = Gtk.TreeStore(str, str)
        self.tree.set_model(self.treestore)

        self.videofinder = None

    def load_records(self):
        try:
            with open(self.database_json_path, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            self.log.warning("File not found: {self.database_json_path}")
            return {}

    def get_file_path(self, name):
        return self.records.get(name)
    
    def destroy(self):
        if self.videofinder is not None:
            self.videofinder.destroy()

    def on_select(self, tr_select):
        db_select = self.get_selected_database()
        if db_select is not None:
            self.switch_to_database(db_select)
    
    def get_selection(self, get_name=False):
        item = self.tree.get_selection()
        if item is None:
            return None
        item = item.get_selected()[1]
        if item is None:
            return None
        if get_name:
            obj_select = self.treestore.get_value(item, 0)
        else:
            obj_select = self.treestore.get_value(item, 2)
        return obj_select

    def switch_to_database(self, vid_select):
        pass
    
    def get_selected_database(self):
        obj_selected = self.get_selection()
        if isinstance(obj_selected, Database):
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
        treestore = Gtk.TreeStore(str, str, str)
        
        for v in self.records:
            name = v
            filename = os.path.basename(self.records[v])
            path_to_file = self.records[v]
            treestore.append(None, (name, filename, path_to_file))

        self.treestore = treestore
        self.tree.set_model(treestore)
        self.tree.expand_all()