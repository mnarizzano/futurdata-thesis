from enum import Enum


class FeedbackType(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
