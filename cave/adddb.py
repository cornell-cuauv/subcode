
import sys
import os

from gi.repository import Gtk, Gdk
from misc.log import with_logging
from cave.libcave.cameralink import camera_map
from cave.meta import MetaParser

__location__ = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0])))

@with_logging
class AddDatabase:
    """
    Dialog for adding a database to directory
    """

    last_path = None # Stores the path of the last opened video

    def validate(self):
        #Validates form input; also sets variables for use higher up
        warning_label = self.builder.get_object("warningLabel")

        self.db_filename = self.db_path.get_filename()
        if not (self.db_filename is not None\
                 and os.path.isfile(self.db_filename)\
                 and self.is_valid_video_file(self.db_filename)):
            warning_label.set_text("Invalid Database File")
            return False

        self.db_name = self.db_name_entry.get_text()
        if self.db_name == "":
            warning_label.set_text("Invalid Video Name")
            return False
        else:
            pass

        return True


    def is_valid_video_file(self, filename):
        valid_extensions = ['.cdb']  # Add more valid video extensions as needed

        # Check if the file has a valid video extension
        _, file_extension = os.path.splitext(filename)
        print(file_extension.lower())
        if file_extension.lower() not in valid_extensions:
            return False
        return True
    
    def cancel_click(self, object, data=None):
        self.window.destroy()

    def ok_click(self, object, data=None):
        if self.validate():
            self.window.destroy()
            AddDatabase.last_path = os.path.dirname(self.db_filename)
            self.log.info("Valid parameters; executing callback")
            self.callback(self)
        else:
            self.log.warning("Invalid parameters specified")
            warning_box = self.builder.get_object("warningBox")
            warning_box.set_visible(True)

    def window_destroy(self, object, data=None):
        self.log.debug("Window closed")
        self.window.destroy()

    def __init__(self, callback, default_folder=None):
        self.gladefile = os.path.join(__location__, "gui/adddb.glade")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)

        # Automatically connect signals to functions defined above
        self.builder.connect_signals(self)

        #Form Elements
        self.db_path = self.builder.get_object("dbPathChooser")
        self.db_name_entry = self.builder.get_object("dbNameEntry")

        #If a previous video is added, open the folder containing that video instead
        if AddDatabase.last_path is not None:
            self.db_path.set_current_folder(AddDatabase.last_path)
        
        #Set default folders for the file-buttons
        elif default_folder is not None:
            self.db_path.set_current_folder(default_folder)
        
        #Get the main window
        self.window = self.builder.get_object("addVideoWindow")
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.show()

        #Link callback
        self.callback = callback

        self.log.debug("Window created")

