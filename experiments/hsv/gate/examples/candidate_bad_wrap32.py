"""Deliberately-subtly-wrong candidate: identical terms, but the combine wraps
at 32 bits instead of 16.  Correct on the vast majority of boards -- the gate
must still fail it and dump a reproducer."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pyleaf
from common import arrays_to_nes


def leaf(col, vir, w, fl):
    return pyleaf.py_eval(arrays_to_nes(col, vir), w, fl, bug="wrap32")
