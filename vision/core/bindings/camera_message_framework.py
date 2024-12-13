from auv_python_helpers import get_library_path
import sys
import cffi
import time
import enum
import numpy as np

from typing import (
    Any,
    Tuple,
    Optional,
)

ffi = cffi.FFI()

ffi.cdef(
    """
extern const char* BLOCK_STUB_CSTR;
extern int SUCCESS;
extern int NO_NEW_FRAME;
extern int FRAMEWORK_DELETED;

typedef struct Block Block;
typedef struct Frame {
    size_t width;        
    size_t height;        
    size_t depth;        
    size_t type_size;        
    uint64_t acquisition_time;
    uint64_t uid;        
    void* data;
} Frame;
Block* create_block(const char* direction, const size_t max_entry_size_bytes);
Block* open_block(const char* direction);
void delete_block(Block* block);
int write_frame(Block* block,
				 uint64_t acquisition_time,
				 size_t width,
				 size_t height,
				 size_t depth,
				 size_t type_size,
				 const unsigned char* data);
int read_frame(Block* block, Frame* frame, bool block_thread);
Frame* create_frame();
void delete_frame(Frame* frame);
uint64_t frame_size(Frame* frame);
"""
)

_dllib: Any = ffi.dlopen(get_library_path("libcamera_message_framework.so"))


class ReadStatus(enum.Enum):
    """Enum wrapper for vision buffer read status"""
    SUCCESS = _dllib.SUCCESS  # type: ignore
    NO_NEW_FRAME = _dllib.NO_NEW_FRAME  # type: ignore
    FRAMEWORK_DELETED = _dllib.FRAMEWORK_DELETED  # type: ignore

class WriteStatus(enum.Enum):
    """Enum wrapper for vision buffer write status"""
    SUCCESS = _dllib.SUCCESS  # type: ignore
    FRAMEWORK_DELETED = _dllib.FRAMEWORK_DELETED  # type: ignore


BLOCK_STUB = ffi.string(_dllib.BLOCK_STUB_CSTR).decode()  # type: ignore


def encode_str(s: str):
    """
    Encodes a string into a numpy array of bytes (uint8).

    Parameters:
        s (str): The input string to be encoded.

    Returns:
        np.ndarray: A numpy array containing the encoded byte values of the string.
    """
    return np.frombuffer(s.encode("utf-8"), dtype=np.uint8)


def decode_str(arr: np.ndarray):
    """
    Decodes a numpy array of bytes (uint8) into a string.

    Parameters:
        arr (np.ndarray): The input numpy array containing byte values to be decoded.

    Returns:
        str: The decoded string from the byte array.
    """
    return arr.tobytes().decode("utf-8")


class BlockAccessor:
    """A volatile memory-backed object (mmap-ed object) capable of being shared
    between multiple processes. Supports writes of numpy arrays up to 3-dimensions
    with underlying data type sizes that are 1, 4, or 8 bytes wide.
    """

    def __init__(
        self,
        direction: str,
        max_entry_size_bytes: Optional[int] = None,
        byte_type: type = np.uint8,
        short_type: type = np.float32,
        long_type: type = np.float64,
        block_thread: bool = False,
    ):
        """Initializes a BlockAccessor that will create/access the volatile-memory
        backed object within a context manager. The behavior of the accessor depends
        on the arguments passed into this initializer.

        Args:
            direction (str): the name given to the mmap object.
            max_entry_size_bytes (Optional[int], optional): bytes to allocate for a frame in the mmap-ed object; if left as None, the system will not allocate any memory, and will wait for the object to be created

            byte_type (type, optional): 1-byte wide data format from this block. Defaults to np.uint8.
            short_type (type, optional): 4-byte wide data format from this block. Defaults to np.float32.
            long_type (type, optional): 8-byte wide data format from this block. Defaults to np.float64.
        """

        assert (max_entry_size_bytes is None) or (
            max_entry_size_bytes > 0
        ), "max_entry_size_bytes, when specified, should be a positive integer"
        assert np.dtype(byte_type).itemsize == 1, "byte type must be 1 byte wide"
        assert np.dtype(short_type).itemsize == 4, "short type must be 4 bytes wide"
        assert np.dtype(long_type).itemsize == 8, "long type must be 8 bytes wide"

        self._direction = direction
        self._max_entry_size_bytes = max_entry_size_bytes
        self._type_lookup = [byte_type, short_type, long_type]

        self._inside_ctx_manager = False
        self._block_ptr = ffi.NULL
        self._frame_ptr = ffi.NULL
        self._frame_data: Optional[np.ndarray] = None
        self._block_thread: bool = block_thread

    @property
    def direction(self) -> str:
        """Get name of the mmap-ed object"""
        return self._direction

    def block_thread(self) -> "BlockAccessor":
        """Implements the builder pattern. Allows read_frame to block the current thread
        when there is no new frame
        """
        self._block_thread = True
        return self

    def unblock_thread(self) -> "BlockAccessor":
        """Implements the builder pattern. Allows read_frame to return immediately if
        there is no new frame.
        """
        self._block_thread = False
        return self

    def write_frame(self, acquisition_time_ms: int, frame: np.ndarray):
        """Write numpy frame to data segment in the mmap-ed object

        Args:
            acquisition_time_ms (int): Time in milliseconds when the frame was acquired
            frame (np.ndarray): Numpy array containing the frame data

        Raises:
            RuntimeError: Thrown when this function is not accessed in a context manager
            RuntimeError: Thrown when the dtype of the frame object is not 1,4, or 8 bytes wide
            RuntimeError: Thrown when the frame object does not have the supported dimensions (1-3)
        """

        if not self._inside_ctx_manager:
            raise RuntimeError(
                f"Attempted to access block while not in a context manager: {__file__}:{sys._getframe(1).f_lineno}"
            )

        if frame.itemsize != 1 and frame.itemsize != 4 and frame.itemsize != 8:
            raise RuntimeError(
                f"np.ndarray dtype size is {frame.itemsize} bytes and not 1, 4, or 8 bytes"
            )

        if len(frame.shape) > 3 or len(frame.shape) == 0:
            raise RuntimeError(
                f"np.ndarray has {len(frame.shape)} dimensions, which does not fall between 1-3 dimensions"
            )

        shape = frame.shape
        height = shape[0]
        width = shape[1] if len(shape) > 1 else 1
        depth = shape[2] if len(shape) > 2 else 1

        write_status = WriteStatus(_dllib.write_frame(  # type: ignore
            self._block_ptr,
            ffi.cast("uint64_t", acquisition_time_ms),
            ffi.cast("size_t", width),
            ffi.cast("size_t", height),
            ffi.cast("size_t", depth),
            ffi.cast("size_t", frame.itemsize),
            ffi.cast("unsigned char*", ffi.from_buffer(frame)),  # type: ignore
        ))

        return write_status

    def read_frame(self) -> Tuple[ReadStatus, Optional[np.ndarray], int]:
        """Read the latest frame, if any, from the data segment in the mmap-ed object.
        If the block_thread property was set to true, this function may register itself as a
        watcher with a few second timeout to try and catch the latest frame.

        Raises:
            RuntimeError: Thrown when this function is not accessed in a context manager

        Returns:
            Tuple[ReadStatus, Optional[np.ndarray], int]: ReadStatus, most recent frame (could be stale, or no frame at all), acquisition time
        """
        if not self._inside_ctx_manager:
            file = __file__
            frame = sys._getframe(1).f_lineno
            raise RuntimeError(
                f"Attempted to access block while not in a context manager: {file}:{frame}"
            )

        read_status = ReadStatus(
            _dllib.read_frame(self._block_ptr, self._frame_ptr, self._block_thread)
        )

        if read_status == ReadStatus.SUCCESS:
            width = self._frame_ptr.width  # type: ignore
            height = self._frame_ptr.height  # type: ignore
            depth = self._frame_ptr.depth  # type: ignore
            itemsize = self._frame_ptr.type_size  # type: ignore
            data = self._frame_ptr.data  # type: ignore
            acquisition_time: int = self._frame_ptr.acquisition_time  # type: ignore

            total_bytes = width * height * depth * itemsize

            frame_buffer = ffi.buffer(data, total_bytes)
            interpret_type = self._type_lookup[itemsize // 4]

            self._acquisition_time = acquisition_time
            self._frame_data = np.frombuffer(
                frame_buffer, dtype=interpret_type  # type: ignore
            ).reshape(height, width, depth)

        return read_status, self._frame_data, self._acquisition_time

    def __str__(
        self,
    ) -> str:
        type_str = [t.__name__ for t in self._type_lookup]
        return f"Accessor(direction={self._direction}, datatypes={':'.join(type_str)})"

    def __enter__(self):
        """Use with context manager """

        if self._inside_ctx_manager:
            raise RuntimeError(
                f"Double dip in context manager: {__file__}: {sys._getframe(1).f_lineno}"
            )

        cstr = ffi.new("char[]", self._direction.encode("utf8"))
        cstr_ptr = ffi.string(cstr)

        if self._max_entry_size_bytes is None:
            retried = False
            retry_count = 0
            self._block_ptr = _dllib.open_block(cstr_ptr)  # type: ignore
            while self._block_ptr == ffi.NULL:
                retry_count += 1

                print(
                    f"trying again to access {self._direction} in 1s, retry count={retry_count:<2}",
                    end="\r",
                    flush=True,
                )
                retried = True
                time.sleep(1)
                self._block_ptr = _dllib.open_block(cstr_ptr)  # type: ignore

            if retried:
                print(f"\nfound {self._direction}!!!", flush=True)

        else:
            self._block_ptr = _dllib.create_block(  # type: ignore
                cstr_ptr, ffi.cast("size_t", self._max_entry_size_bytes)
            )

            if self._block_ptr == ffi.NULL:
                raise RuntimeError(f"Failed to access {self._direction}")

        self._frame_ptr = _dllib.create_frame()  # type: ignore
        self._acquisition_time = 0
        self._frame_data = None
        self._inside_ctx_manager = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._block_ptr != ffi.NULL:
            _dllib.delete_block(self._block_ptr)  # type: ignore

        if self._frame_ptr != ffi.NULL:
            _dllib.delete_frame(self._frame_ptr)  # type: ignore

        self._block_ptr = ffi.NULL;
        self._frame_ptr = ffi.NULL;
        self._inside_ctx_manager = False
    