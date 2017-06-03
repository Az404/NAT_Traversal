from enum import Enum


class Operation(Enum):
    SEND_HELLO = 0
    WAIT_HELLO = 1
    BIND = 2
    UPDATE_ADDR = 3


class OperationResult(Enum):
    OK = 0
    FAIL = 1
