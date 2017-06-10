from enum import Enum


class Operation(Enum):
    SEND_HELLO = 0
    WAIT_HELLO = 1
    BIND = 2
    ANNOUNCE_ADDR = 3
    UPDATE_ADDR = 4
    FINISH = 5


class OperationResult(Enum):
    OK = 0
    FAIL = 1
