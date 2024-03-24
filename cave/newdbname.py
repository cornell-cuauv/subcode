
import sys
import os

from gi.repository import Gtk, Gdk
from misc.log import with_logging

__location__ = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0])))

@with_logging
class AddDatabaseName:
    """
    Dialog for adding a database to directory
    """
    def validate(self):
        #Validates form input; also sets variables for use higher up
        warning_label = self.builder.get_object("warningLabel")

        self.db_name = self.db_name_entry.get_text()
        if self.db_name == "":
            warning_label.set_text("Invalid Video Name")
            return False
        else:
            pass
        return True
    
    def cancel_click(self, object, data=None):
        self.window.destroy()

    def ok_click(self, object, data=None):
        if self.validate():
            self.window.destroy()
            self.log.info("Valid parameters; executing callback")
            self.callback(self)
        else:
            self.log.warning("Invalid parameters specified")
            warning_box = self.builder.get_object("warningBox")
            warning_box.set_visible(True)

    def window_destroy(self, object, data=None):
        self.log.debug("Window closed")
        self.window.destroy()

    def __init__(self, callback, path=None, default_folder=None):
        self.gladefile = os.path.join(__location__, "gui/newdbname.glade")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.gladefile)

        # Automatically connect signals to functions defined above
        self.builder.connect_signals(self)
        self.path = path

        #Form Elements
        self.db_name_entry = self.builder.get_object("dbNameEntry")
        
        #Get the main window
        self.window = self.builder.get_object("addVideoWindow")
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.show()

        #Link callback
        self.callback = callback

        self.log.debug("Window created")

