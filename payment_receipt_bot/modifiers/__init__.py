"""
HTML Modifiers Package
"""
from .base_modifier import BaseModifier
from .gpay_modifier import GPayModifier
from .phonepe_modifier import PhonePeModifier
from .slice_modifier import SliceModifier
from .supermoney_modifier import SuperMoneyModifier
from .payzapp_modifier import PayZappModifier
from .navi_modifier import NaviModifier

MODIFIERS = {
    "gpay": GPayModifier,
    "phonepe": PhonePeModifier,
    "slice": SliceModifier,
    "supermoney": SuperMoneyModifier,
    "payzapp": PayZappModifier,
    "navi": NaviModifier,
}
