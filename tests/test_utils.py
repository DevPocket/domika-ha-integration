# vim: set fileencoding=utf-8
"""
tests.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import enum

from custom_components.domika import utils


def test_flatten():
    class TmpFlag(enum.IntFlag):
        ONE = 1
        TWO = 2

    class TmpEnum(enum.Enum):
        DOG = 1
        CAT = 'meow'

    """Test json dict flattening."""
    assert utils.flatten_json(
        {
            'a': {
                'b': {
                    'c': 'test',
                    'int_flag': TmpFlag.ONE | TmpFlag.TWO,
                    'str_list': ['1', '2'],
                    'float_list': [0.3, 0.5],
                    'int_flag_list': [TmpFlag.ONE | TmpFlag.TWO, TmpFlag.ONE],
                    'enum_list': [TmpEnum.DOG, TmpEnum.CAT],
                    'enum': TmpEnum.CAT,
                },
                'unwanted': {
                    'buggy stuff': 'DEAD_BEEF',
                    'nested': {
                        'ignored': 'too',
                    },
                },
                'arr': [1, 2, 3],
            },
            'blip': 'blop',
        },
        exclude={'a.unwanted'},
    ) == {
        'a.b.c': 'test',
        'a.b.int_flag': '3',
        'a.b.str_list': "['1', '2']",
        'a.b.float_list': '[0.3, 0.5]',
        'a.b.int_flag_list': '[3, 1]',
        'a.b.enum_list': "[1, 'meow']",
        'a.b.enum': 'meow',
        'a.arr': '[1, 2, 3]',
        'blip': 'blop',
    }
