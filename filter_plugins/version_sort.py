from distutils.version import LooseVersion


def version_sort(l):
    return sorted(l, key=LooseVersion)


class FilterModule(object):
    def filters(self):
        return {"version_sort": version_sort}
