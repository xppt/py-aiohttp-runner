import pickle
import sys
from io import BytesIO
from typing import Any


def serialize_obj(obj: Any) -> str:
    main_module_name = ''
    main_module = sys.modules.get('__main__')
    if main_module is not None:
        spec = getattr(main_module, '__spec__', None)
        name = getattr(spec, 'name', None)
        if isinstance(name, str) and ':' not in name:
            main_module_name = name

    dump = pickle.dumps(obj)

    return f'{main_module_name}:{dump.hex()}'


def deserialize_obj(value: str) -> Any:
    main_module, hex_dump = value.split(':', 1)
    dump = bytes.fromhex(hex_dump)

    class _Unpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if module == '__main__' and main_module:
                module = main_module

            return super().find_class(module, name)

    return _Unpickler(BytesIO(dump)).load()
