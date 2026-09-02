# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""cmdline_to_json filter — DEPRECATED.

This filter has been moved to the ``redhatci.ocp`` Ansible collection.
Use ``redhatci.ocp.cmdline_to_json`` instead.

This shim is kept for backward compatibility and will be removed in a
future release.
"""

import warnings
from json import dumps

_DEPRECATION_MSG = (
    "The cmdline_to_json filter in dci-ansible is deprecated. "
    "Use redhatci.ocp.cmdline_to_json from the "
    "ansible-collection-redhatci-ocp collection instead."
)

try:
    from ansible.utils.display import Display
    _display = Display()
except ImportError:
    _display = None


def cmdline_to_json(cmdline=""):
    """Parse a kernel command line string and return a JSON object.

    .. deprecated::
        Use ``redhatci.ocp.cmdline_to_json`` instead.
    """
    warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    if _display is not None:
        _display.deprecated(
            _DEPRECATION_MSG,
            version="3.0.0",
            collection_name="dci-ansible",
        )

    kernel = {}

    for item in cmdline.split():
        if "=" in item:
            k, v = item.split("=", 1)
            # Handle comma-separated values for specific keys
            if "," in v and k not in ["BOOT_IMAGE"]:
                v = v.split(",")
        else:
            k = item
            v = ""

        # Handle nested keys - any key with dots creates nested structure
        if "." in k:
            parts = k.split(".")
            current = kernel
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = v
        else:
            kernel[k] = v

    return dumps(kernel)


class FilterModule(object):
    def filters(self):
        return {"cmdline_to_json": cmdline_to_json}
