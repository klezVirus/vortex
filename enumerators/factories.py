import traceback
from pydoc import locate

from enumerators.enumerator import VpnEnumerator


class VpnEnumeratorFactory:
    @staticmethod
    def from_name(name: str, target, group=None) -> VpnEnumerator:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.vpn.{name}.{name.capitalize()}Enumerator"
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class(target, group=group)
        except:
            # traceback.print_exc()
            return None


class OfficeEnumeratorFactory:
    @staticmethod
    def from_name(name: str, target, group=None) -> VpnEnumerator:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.office.{name}.{name.capitalize()}Enumerator"
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class(target, group=group)
        except Exception as e:
            # traceback.print_exc()
            # print(e.__class__.__name__ + ": " + e.__str__())
            return None
