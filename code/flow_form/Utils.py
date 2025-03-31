import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc



alpha = "abcdefghijklmnopqrstuvwxyz"


import json
def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def delete_group_items(name):
    a_group = sc.doc.Groups.FindName(name)
    if not a_group:
        pass
    else:
        group_items = sc.doc.Objects.FindByGroup(a_group.Index)
        if len(group_items) > 0:
            for item in group_items:
                sc.doc.Objects.Delete(item)


class DataOutput:
    pass