import time
import signal
import glob
import argparse
import threading
import contextlib
import numpy as np

from cv2 import UMat as cv2Mat  # type: ignore
from abc import ABC, abstractmethod
from typing import (
    List,
    Dict,
    OrderedDict as TOrderedDict,
    Union,
    Tuple,
    Callable,
    Any,
    Optional,
    Deque,
)
from vision.core.bindings.camera_message_framework import (
    BlockAccessor,
    BLOCK_STUB,
    ReadStatus,
)
from vision.core.tuners import TunerBase, IntTuner, DoubleTuner, BoolTuner
from vision.utils.helpers import from_umat
from collections import OrderedDict, deque
from dataclasses import dataclass

from auvlog.client import log as auvlog
from auvlog.client import Logger


@dataclass
class VideoSource:
    """data class representing how we should decode the messages from the vision buffer.
    Note: Arbitrarily long strings can be encoded with a byte array (not tested with UTF-8,
    but it is theoretically possible).
    """

    name: str

    byte_type: type = np.uint8
    """data type to treat 1 byte wide messages"""

    short_type: type = np.float32
    """data type to treat 4 byte wide messages"""

    long_type: type = np.float64
    """data type to treat 8 byte wide messages"""

    @classmethod
    def create(cls, source_str: Union[str, "VideoSource"]) -> "VideoSource":
        """create a video source object from a correctly formatted string
        the format should be the name, followed by ":" delimitated data types
        like u8, i8, u32, i32, f32, u64, i64, f64. Example: "forward:f32" means
        to decode 4 byte wide datatypes from forward as f32."""
        if isinstance(source_str, VideoSource):
            return source_str

        if ":" not in source_str:
            name = source_str
            return VideoSource(name)

        name, types = source_str.split(":", maxsplit=1)

        if "u8" in types:
            b_type = np.uint8
        elif "i8" in types:
            b_type = np.int8
        else:
            b_type = np.uint8

        if "u32" in types:
            s_type = np.uint32
        elif "i32" in types:
            s_type = np.int32
        elif "f32" in types:
            s_type = np.float32
        else:
            s_type = np.float32

        if "u64" in types:
            l_type = np.uint64
        elif "i64" in types:
            l_type = np.int64
        elif "f64" in types:
            l_type = np.float64
        else:
            l_type = np.float64

        return VideoSource(name, b_type, s_type, l_type)

    @classmethod
    def into_accessor(cls, instn: "VideoSource"):
        """Transform an accessor object into a BlockAccessor object in read mode."""
        return BlockAccessor(
            instn.name,
            byte_type=instn.byte_type,
            short_type=instn.short_type,
            long_type=instn.long_type,
        )


class ModuleManager:
    """Utility class used by vision modules to read from video sources, post output frames, and send tuner updates."""

    def __init__(
        self,
        module_name: str,
        video_sources: List[VideoSource],
        tuner_sources: List[TunerBase],
    ):
        """Create a module that can interface with a "ModuleReader"

        Args:
            module_name (str): Name of the module
            video_sources (List[VideoSource]): video inputs into the module, the class will try and create a "BlockAccessor" in read mode for each source
            tuner_sources (List[TunerBase]): tuner inputs into the module, the class will try and create a "BlockAccessor" in write mode for each source

        Raises:
            RuntimeError: If there are duplicate video source names (ill defined because forward:f32 and forward:f64 contradict each other)
            RuntimeError: If there are duplicate tuner names of the same type (ill defined because it's difficult to differentiate as the programmer)
        """

        # modules share the /dev/shm/ directory with capture sources, so we need a way to different between the two types of message buffers
        # solution is to have every "module" message buffer be prefixed with the "module" keyword

        self._module_name = "module_" + module_name
        self._post_name = self._module_name + "_post"
        self._tune_name = self._module_name + "_tune"
        self._first = True

        self._video_sources: Dict[str, VideoSource] = {
            vs.name: vs for vs in video_sources
        }

        self._tuner_sources: Dict[str, TunerBase] = {
            ts.name: ts for ts in tuner_sources
        }

        self._video_accessor: Dict[str, BlockAccessor] = {
            vs.name: VideoSource.into_accessor(vs) for vs in video_sources
        }

        # encode an index into the tuner name so that the webgui knows how to order the 
        # tuners
        self._tuner_accessor: Dict[str, BlockAccessor] = {
            ts.name: BlockAccessor(
                f"{self._tune_name}%{idx}%{str(ts)}",
                max_entry_size_bytes=ts.byte_size(),
            )
            for idx, ts in enumerate(tuner_sources)
        }

        # initially empty, but expected to grow
        self._post_accessor: Dict[str, BlockAccessor] = {}

        if len(self._video_sources) != len(video_sources):
            raise RuntimeError("cannot have multiple video sources of the same name")

        if len(self._tuner_sources) != len(tuner_sources):
            raise RuntimeError("cannot have multiple tuner types of the same name")

        self._post_accessor: Dict[str, BlockAccessor] = {}
        self._exit_stack = contextlib.ExitStack()
        self._inside_ctx = False

    def post(self, name: str, idx: int, acquisition_time: int, data: np.ndarray):
        if not self._inside_ctx:
            raise RuntimeError(
                f"attempted to access ModuleManager while not in a context manager"
            )

        if name in self._post_accessor:
            self._post_accessor[name].write_frame(acquisition_time, data)
        else:
            accessor = BlockAccessor(f"{self._post_name}%{idx}%{name}", data.nbytes)
            self._exit_stack.enter_context(accessor)
            self._post_accessor[name] = accessor
            self._post_accessor[name].write_frame(acquisition_time, data)

    def read_messages(self) -> List[Tuple[str, Tuple[ReadStatus, np.ndarray, int]]]:
        if not self._inside_ctx:
            raise RuntimeError(
                f"attempted to access ModuleManager while not in a context manager"
            )

        # deserialize tuners
        for name, ta in self._tuner_accessor.items():
            result, frame, _ = ta.read_frame()

            if result == ReadStatus.FRAMEWORK_DELETED:
                raise RuntimeError("Unexpected deleted Tuner")

            if frame is not None:
                self._tuner_sources[name].deserialize(frame.tobytes("C"))

        # deserialize frame information
        ret = []
        for accessor in self._video_accessor.values():
            read_result, data, acquisition_time = accessor.read_frame()

            if read_result == ReadStatus.FRAMEWORK_DELETED:
                raise RuntimeError(f"{accessor.direction} was marked for deletion")

            if data is not None:
                ret.append((accessor.direction, (read_result, data, acquisition_time)))

        return ret

    def __getitem__(self, key: str) -> Any:
        return self._tuner_sources[key].value

    def __str__(self) -> str:
        return f"ModuleManager(name={self._module_name}, video_sources={self._video_sources}, tuner_sources={self._tuner_sources})"

    def __enter__(self):
        if self._inside_ctx:
            raise RuntimeError(f"double dipped in context manager for ModuleManager")

        self._inside_ctx = True

        self._exit_stack.__enter__()

        try:
            for va in self._video_accessor.values():
                self._exit_stack.enter_context(va)

            for ta in self._tuner_accessor.values():
                self._exit_stack.enter_context(ta)

            # write tuner to accessors
            if self._first:
                self._first = False;
                for name, ts in self._tuner_sources.items():
                    data = np.frombuffer(ts.serialize(), dtype=np.uint8)

                    ta = self._tuner_accessor[ts.name]
                    ta.write_frame(int(time.monotonic() * 1000), data)

        except KeyboardInterrupt or Exception as e:
            # clean up
            for _, va in self._video_accessor.items():
                va.__exit__(None, None, None)

            for _, ta in self._tuner_accessor.items():
                ta.__exit__(None, None, None)

            raise e

        return self

    def __exit__(self, type, value, traceback):
        self._exit_stack.__exit__(type, value, traceback)
        self._post_accessor.clear()
        self._inside_ctx = False


class ModuleReader:
    """Utility class used to read frames and tuner information from "ModuleManager", and communicate tuner updates
    with the corresponding Module."""

    def __init__(self, module_name: str):

        if module_name not in ModuleReader.get_active_modules():
            raise RuntimeError("Module name is not active")

        self._base_module_name = module_name
        self._module_name = f"module_{module_name}"
        self._post_name = f"{self._module_name}_post%"
        self._tune_name = f"{self._module_name}_tune%"
        self._quit_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._post_udls: List[Callable[[str, str, int, np.ndarray], None]] = []
        self._tuner_udls: List[Callable[[str, str, int, TunerBase], None]] = []

        # in the format name, (idx, accessor)
        self._all_posts: Dict[str, Tuple[int, BlockAccessor]] = {}

        # in the format name, (idx, accessor, tuner)
        self._all_tuners: Dict[str, Tuple[int, BlockAccessor, TunerBase]] = {}
        self._tuner_guard = False
        self._framework_deleted = False

        # populate the tuners and posters
        for active_post in self.active_posts:
            idx, name = self.parse_post_name(active_post)
            self._all_posts[name] = (idx, BlockAccessor(active_post))

        for active_tuner in self.active_tuners:
            idx, tuner_type, name = self.parse_tune_name(active_tuner)
            self._all_tuners[name] = (idx, BlockAccessor(active_tuner), tuner_type)

    @classmethod
    def get_active_modules(cls):
        return list(
            set(map(lambda x: x.split("_")[3], glob.glob(f"{BLOCK_STUB}module_*")))
        )

    @property
    def active_posts(self) -> List[str]:
        prefix = BLOCK_STUB + self._post_name
        glob_rule = prefix + "*"
        return [file[len(BLOCK_STUB) :] for file in glob.glob(glob_rule)]

    @property
    def active_tuners(self):
        prefix = BLOCK_STUB + self._tune_name
        glob_rule = prefix + "*"
        return [file[len(BLOCK_STUB) :] for file in glob.glob(glob_rule)]
    
    @property
    def framework_deleted(self):
        return self._framework_deleted

    def parse_post_name(self, s: str) -> Tuple[int, str]:
        _, idx, post_name = s.split("%")
        return (int(idx), post_name)

    def parse_tune_name(self, s: str) -> Tuple[int, TunerBase, str]:
        _, idx, tuner_str = s.split("%")
        tuner_type, tuner_name = tuner_str.split("_", maxsplit=1)

        if tuner_type == "IntTuner":
            tuner_type = IntTuner(tuner_name, 0)
        elif tuner_type == "DoubleTuner":
            tuner_type = DoubleTuner(tuner_name, 0)
        else:
            tuner_type = BoolTuner(tuner_name, False)

        return (int(idx), tuner_type, tuner_name)

    def register_post_udl(self, udl: Callable[[str, str, int, np.ndarray], None]):
        self._post_udls.append(udl)

    def register_tuner_udl(self, udl: Callable[[str, str, int, TunerBase], None]):
        self._tuner_udls.append(udl)

    def run_forever(self, fps: int = 60):
        if self._thread is not None:
            raise RuntimeError("cannot run already running module reader")

        self._quit_flag = threading.Event()
        self._thread = threading.Thread(target=self._loop, args=(fps,))
        self._thread.start()

    def allow_resend_tuners_once(self):
        self._tuner_guard = True

    def update_tuner_value(self, name: str, value: Any):
        _, accessor, tuner = self._all_tuners[name]
        tuner._current_value = value

        data = np.frombuffer(tuner.serialize(), dtype=np.uint8)
        accessor.write_frame(int(time.monotonic() * 1000), data)

    def _loop(self, fps: int):
        with contextlib.ExitStack() as exit_stack:
            for _, accessor in self._all_posts.values():
                exit_stack.enter_context(accessor)

            for _, accessor, _ in self._all_tuners.values():
                exit_stack.enter_context(accessor)

            WAIT_TIME = 1.0 / fps
            while not self._quit_flag.is_set():
                time_now = time.monotonic()

                for name, (idx, accessor) in self._all_posts.items():
                    result = accessor.read_frame()

                    if result is None:
                        continue

                    read_result, read_data, _ = result
                    if read_result == ReadStatus.SUCCESS and read_data is not None:
                        for cbck in self._post_udls:
                            cbck(self._base_module_name, name, idx, read_data)
                    elif read_result == ReadStatus.FRAMEWORK_DELETED:
                        print(f"ModuleReader: {self._base_module_name} framework deleted")
                        self._framework_deleted = True
                        self._quit_flag.set()

                flag = False
                for name, (idx, accessor, tuner) in self._all_tuners.items():
                    result = accessor.read_frame()

                    if result is None:
                        continue

                    read_result, read_data, _ = result
                    if (
                        self._tuner_guard or read_result == ReadStatus.SUCCESS
                    ) and read_data is not None:
                        flag = flag or self._tuner_guard
                        tuner.deserialize(read_data.tobytes("C"))
                        for cbck in self._tuner_udls:
                            cbck(self._base_module_name, name, idx, tuner)
                    elif read_result == ReadStatus.FRAMEWORK_DELETED:
                        print(f"ModuleReader: {self._base_module_name} framework deleted")
                        self._framework_deleted = True
                        self._quit_flag.set()

                if flag:
                    self._tuner_guard = False

                time_end = time.monotonic()
                time_elapsed = time_end - time_now
                time.sleep(max(0, WAIT_TIME - time_elapsed))

    def unblock(self):
        if self._thread is None:
            print(f"[WARNING]: {self._module_name} was already terminated")
            return

        self._quit_flag.set()
        self._thread.join()
        self._thread = None

    def __del__(self):
        if self._thread is not None:
            print(
                "[WARNING]: object garbage collected without freeing underlying resources"
            )

            self._quit_flag.set()
            self._thread.join()


VideoOrdDict_T = TOrderedDict[str, BlockAccessor]
TunerOrdDict_T = TOrderedDict[str, Tuple[TunerBase, BlockAccessor]]


@dataclass
class VideoSourceMetadata:
    _frames_read: int = 0
    _shape: Tuple[int, int] = (1, 1)
    _acquisition_times: Deque[int] = deque(maxlen=30)
    _dead_counter = 0

    def update(self, mat: np.ndarray, acquisition_time: int):
        """update the metadata with the new frame"""
        self._acquisition_times.append(int(time.monotonic() * 1000 - acquisition_time))
        self._shape = (mat.shape[0], mat.shape[1])
        self._frames_read += 1
        self._dead_counter = max(0, self._dead_counter - 1)

    def mark_as_dead(self):
        """marks the vision module as dead and returns if the vision was stable before"""
        alive = self._dead_counter == 0
        self._dead_counter = 3
        return alive

    def get_latency(self) -> int:
        """returns the running average latency of this video source in ms of the last 10 frames"""
        average = sum(self._acquisition_times) / len(self._acquisition_times)
        return int(average)

    def normalize_axis(self, coord: float, axis: int) -> float:
        """Converts exact coordinates to normalized coordinates.

        Args:
            coord (float): original coordinate
            axis (int): 0 for x-axis, 1 for y-axis

        Returns:
            (float): normalized coordinates
        """
        return (coord - self._shape[1 - axis] / 2) / self._shape[1]

    def normalize_coord(self, coord: Tuple[float, float]) -> Tuple[float, float]:
        """Convert exact coordinates to normalized coordinates

        Args:
            coord (Tuple[float, float]): should in the format (row, height), or (y, x)

        Returns:
            Tuple[float, float]: normalized coordinates in the format (y, x)
        """
        return self.normalize_axis(coord[0], 1), self.normalize_axis(coord[1], 0)


class ModuleBase(ABC):
    """_summary_

    Args:
        ABC (_type_): _description_
    """

    def __init__(
        self,
        video_sources: List[Union[VideoSource, str]] = [],
        tuners: List[TunerBase] = [],
        fps: int = 10,
    ):
        """_summary_

        Args:
            video_sources (List[VideoSource], optional): _description_. Defaults to [].
            tuners (List[TunerBase], optional): _description_. Defaults to [].
            fps (int, optional): _description_. Defaults to 10.
        """
        # parse arguments
        parser = argparse.ArgumentParser(
            f"{__file__}",
            description="CLI to run this particular vision module",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        parser.add_argument(
            "-f",
            "--fps",
            type=int,
            default=fps,
            help="maximum fps to run (capped at speed of video sources) (recommended to specify a value <= 10)",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="display debug messages"
        )
        parser.add_argument(
            "--enable-performance",
            action="store_true",
            help="disable posting to help with performance during competition runs",
        )

        parser.add_argument(
            "sources",
            nargs="*",
            type=str,
            help=(
                "Specifies video sources. If left empty, default sources will be used.\n"
                "Provide sources in the following format: {name}:<type>, where:\n"
                "\t- {name}: A unique identifier for the source (e.g., 'camera1').\n"
                "\t- <type1>: Specifies the data type for the first field (choose from 'u8', 'i8')\n"
                "\t- <type2>: Specifies the data type for the second field (choose from 'u32', 'i32', or 'f32').\n"
                "\t- <type3>: Specifies the data type for the third field (choose from 'u64', 'i64', or 'f64').\n\n"
                "Example: 'forward:f64' interprets 8 byte wide as f64 and uses 1 and 4 byte wide defaults\n"
                "Example: 'forward:i8:f32' uses 8 byte wide defaults"
            ),
        )
        args = parser.parse_args()

        if "_" in self.__class__.__name__:
            raise RuntimeError(
                f"Class name '{self.__class__.__name__}'cannot have an underscore"
            )
        arg_sources: List[str] = args.sources

        src = arg_sources if len(arg_sources) > 0 else video_sources
        src = list(map(VideoSource.create, src))

        self._name = (
            self.__class__.__name__ + "-on-" + "-".join(map(lambda x: x.name, src))
        )

        # initialize fields
        self._fps: int = args.fps if args.fps else fps
        self._verbose: bool = args.verbose
        self._module_manager = ModuleManager(self._name, src, tuners)
        self._post_queue: TOrderedDict[str, np.ndarray] = OrderedDict()
        self._performance_enabled = args.enable_performance
        self._retry = True

        self._video_metadata = {s.name: VideoSourceMetadata() for s in src}
        self._current_direction = ""

    @property
    def tuners(self):
        return self._module_manager

    def __call__(self):
        logger = auvlog.__getattr__(self._name)
        logger(f"Running {self._name}", True)

        if self._performance_enabled:
            logger(f"Module running in performance mode", True)

        original_sigint_handler = signal.getsignal(signal.SIGINT)
        quit_flag = threading.Event()

        def quit():
            quit_flag.set()

        def sigh(*args):
            logger(
                f"Caught signal: {args[0]}. It may take up to 2 seconds to clean up.",
                self._verbose,
            )
            quit()

        logger(f"Target FPS = {self._fps}", self._verbose)

        while self._retry:
            self._retry = False
            quit_flag.clear()
            with self._module_manager:
                signal.signal(signal.SIGINT, sigh)
                logger(f"Registered SIGINT handler", self._verbose)
                logger(f"Initialized module manager {self._module_manager}", self._verbose)
                args = quit_flag, logger
                main_thread = threading.Thread(target=self._loop, args=args)
                main_thread.start()
                main_thread.join()
            
            if self._retry:
                signal.signal(signal.SIGINT, original_sigint_handler)
                logger(f"Unregistered SIGINT handler", self._verbose)

        logger(f"Cleaning {self.__class__.__name__}", True)

    def _loop(self, quit_flag: threading.Event, logger: Logger):
        while not quit_flag.is_set():
            start = time.monotonic()

            try:
                video_messages = self._module_manager.read_messages()
            except RuntimeError as e:
                logger(f"Error: {e}", True)
                quit_flag.set()
                self._retry = True
                break

            for source_name, (read_status, image, acq_time) in video_messages:
                if read_status == ReadStatus.SUCCESS:
                    self._video_metadata[source_name].update(image, acq_time)
                    self._current_direction = source_name
                    self.process(source_name, image)
                elif read_status == ReadStatus.NO_NEW_FRAME:
                    if self._video_metadata[source_name].mark_as_dead():
                        logger(
                            f"{source_name} appears to be slow or dead!", self._verbose
                        )

            for idx, (name, data) in enumerate(self._post_queue.items()):
                self._module_manager.post(name, idx, int(time.monotonic() * 1000), data)
            self._post_queue.clear()

            time.sleep(max((1 / self._fps) - (time.monotonic() - start), 0))

    def post(self, name: str, image: Union[np.ndarray, cv2Mat]):
        """Send a message to the WebGui. Note that the image is copied,
        so post is disabled if performance mode is on.

        Args:
            name (str): name to display
            image (Union[np.ndarray, cv2Mat]): image data
        """
        if self._performance_enabled:
            return

        if "%" in name:
            raise RuntimeError("Cannot have % in name")
        if type(image) is cv2Mat:
            image = from_umat(image).astype(np.uint8)
        else:
            image = np.array(image, np.uint8, copy=True, order="C", ndmin=1)

        self._post_queue[name] = image

    def get_latency(self) -> int:
        """return the latency in ms for the current direction"""
        return self._video_metadata[self._current_direction].get_latency()

    def normalize(self, coordinate: Tuple[float, float]) -> Tuple[float, float]:
        """Convert exact coordinates to normalized coordinates for the current direction

        Args:
            coord (Tuple[float, float]): should in the format (row, height), or (y, x)

        Returns:
            Tuple[float, float]: normalized coordinates in the format (y, x)
        """
        return self._video_metadata[self._current_direction].normalize_coord(coordinate)

    def normalize_axis(self, coordinate: float, axis: int) -> float:
        """Converts exact coordinates to normalized coordinates for the current direction.

        Args:
            coord (float): original coordinate
            axis (int): 0 for x-axis, 1 for y-axis

        Returns:
            (float): normalized coordinates
        """
        return self._video_metadata[self._current_direction].normalize_axis(
            coordinate, axis
        )

    @abstractmethod
    def process(self, direction: str, image: np.ndarray):
        """Method every user should override

        Raises:
            NotImplementedError: raised if method not overridden
        """
        raise NotImplementedError("ModuleBase.process")
