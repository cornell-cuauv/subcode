import hashlib
import cv2
import subprocess
import os
from misc import log
from misc.log import with_logging

@with_logging
class Encoder:
    def log_warning(self):
        self.log.warning("Source file metadata is incomplete, running an encoding script to restore data. This should be a one time event for a given file and should not happen again.")

def encode(filename):
    Encoder().log_warning() # log message notification
    
    directory_path = os.path.dirname(filename)
    temp_output_path = os.path.join(directory_path, "temp_video.avi")
    ffmpeg_command = [
        "ffmpeg",
        "-i", filename,
        "-c:v", "copy",
        "-c:a", "copy",
        "-loglevel", "quiet",
        temp_output_path  # Temporary output file
    ]
    subprocess.run(ffmpeg_command, check=True)
    os.replace(temp_output_path, filename)
    pass

def verify_video(filename):
    cap = cv2.VideoCapture(filename)

    # Incorrectly encoded files: re-encode using ffmpeg
    if (int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 0):
        encode(filename)
        cap = cv2.VideoCapture(filename)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    #TODO: Verify accuracy of this
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    success, test_frame = cap.read()
    # assert(success)
    height = len(test_frame)
    # assert(height == len(test_frame))
    width = len(test_frame[0])
    # assert(width == len(test_frame[0]))

    nchannels = len(test_frame[0][0]) #should be 3 elements per frame

    return (cap, width, height, length, nchannels)

def hash_video(filename):
    cap = cv2.VideoCapture(filename)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if length < 10:
        print("Unable to hash video; bad length!")
        return ""

    hasher = hashlib.md5()
    for i in range(0, length, length // 10): #python2 to python3
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        success, frame = cap.read()
        if success:
            hasher.update(frame)
        else:
            print("Unable to hash full video, video incomplete?")
            break

    return hasher.hexdigest()
