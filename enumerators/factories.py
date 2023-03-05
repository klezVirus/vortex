from pydoc import locate
from typing import Union

from enumerators.interfaces.enumerator import VpnEnumerator
from enumerators.interfaces.searcher import Searcher


class VpnEnumeratorFactory:
    @staticmethod
    def from_name(name: str, target, group=None) -> Union[VpnEnumerator, None]:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.vpn.{name.lower()}.{name.capitalize()}Enumerator"
            # print(enumerator_class_string)
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class(target, group=group)
        except TypeError as e:
            if str(e).find("NoneType") != -1:
                return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e.__class__.__name__ + ": " + e.__str__())
            return None


class OfficeEnumeratorFactory:
    @staticmethod
    def from_name(name: str, target, group=None) -> Union[VpnEnumerator, None]:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.office.{name.lower()}.{name.capitalize()}Enumerator"
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class(target, group=group)
        except Exception as e:
            # traceback.print_exc()
            # print(e.__class__.__name__ + ": " + e.__str__())
            return None


class MiscEnumeratorFactory:
    @staticmethod
    def from_name(name: str, target, group=None) -> Union[VpnEnumerator, None]:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.misc.{name.lower()}.{name.capitalize()}Enumerator"
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class(target, group=group)
        except Exception as e:
            # traceback.print_exc()
            # print(e.__class__.__name__ + ": " + e.__str__())
            return None


class SearcherFactory:
    @staticmethod
    def from_name(name: str) -> Union[Searcher, None]:
        enumerator_class = None
        try:
            enumerator_class_string = f"enumerators.search.{name.lower()}.{name.capitalize()}"
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class()
        except Exception as e:
            import traceback
            traceback.print_exc()
            # print(e.__class__.__name__ + ": " + e.__str__())
            return None
