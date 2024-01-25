import importlib.metadata


def entry_points(group=None, name=None):
    result = importlib.metadata.entry_points()
    if isinstance(result, dict):
        if group is not None:
            group_result = result.get(group, [])
            if name is not None:
                return [entry for entry in group_result if entry.name == name]
            return group_result

    selectors = {}
    if group is not None:
        selectors["group"] = group
    if name is not None:
        selectors["name"] = name
    return result.select(**selectors)


def get_entry_point_module(entry_point):
    try:
        return entry_point.module
    except AttributeError:
        return entry_point.pattern.match(entry_point.value).group("module")
