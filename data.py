from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Dict, List, Tuple, Union


@dataclass_json
@dataclass
class Hobby:
    type: str
    desc: str

    def pretty_desc(self):
        print("yoyo, this hobby is dope: {}".format(self.desc))


@dataclass_json
@dataclass
class Person:
    name: str
    age: int
    hobbies: List[Hobby]


p = Person(
    'Albert',
    42,
    [
        Hobby(
            'pingpong',
            'slammo'
        ),
        Hobby(
            'tennis',
            'whammo'
        )
    ]
)

print(
    p.to_json()
)

j = p.to_json()

person = Person.from_json(j)
[
    h.pretty_desc()
    for h in person.hobbies
]
