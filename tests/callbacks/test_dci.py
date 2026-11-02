from callback.dci import CallbackModule
from ansible import constants as C


def test_banner_success():
    cb = CallbackModule()
    cb.banner("a message")

    assert (cb._name == "a message")


def test_banner_error():

    class MyCallback(CallbackModule):
        def __init__(self):
            super(CallbackModule, self).__init__()
            self._color = C.COLOR_ERROR
            self._name = 'a_name'
            self._content = 'this is the content'
            self.filename = ""
            self._warn_prefix = False
            self._item_failed = False
            self._item_actioned = False
            self._task_failed = False
            self._task_unreachable = False

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (cb.filename == "failed/a_name")


def test_banner_error_then_include():
    """A failed task followed by an 'included:' line (COLOR_SKIP) must still be
    recorded as failed/, even though the last color seen is not COLOR_ERROR.
    Reproduces a failing 'include_tasks' whose failure was hidden."""

    class MyCallback(CallbackModule):
        def __init__(self):
            super(CallbackModule, self).__init__()
            # the include printed "included: <file>" after the fatal line
            self._color = C.COLOR_SKIP
            self._name = 'a_name'
            self._content = 'this is the content'
            self.filename = ""
            self._warn_prefix = False
            self._item_failed = False
            self._item_actioned = True
            self._task_failed = True
            self._task_unreachable = False

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (cb.filename == "failed/a_name")


def test_banner_ignored_is_not_failed():
    """An ignored failure (ignore_errors) does not set _task_failed, so it must
    not be recorded as failed/."""

    class MyCallback(CallbackModule):
        def __init__(self):
            super(CallbackModule, self).__init__()
            # the "...ignoring" line is printed with COLOR_SKIP
            self._color = C.COLOR_SKIP
            self._name = 'a_name'
            self._content = 'this is the content'
            self.filename = ""
            self._warn_prefix = False
            self._item_failed = False
            self._item_actioned = False
            self._task_failed = False
            self._task_unreachable = False

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (not cb.filename.startswith("failed/"))


def test_banner_error_loop():

    class MyCallback(CallbackModule):
        def __init__(self):
            super(CallbackModule, self).__init__()
            self._color = C.COLOR_CHANGED
            self._name = 'a_name'
            self._content = """changed: [localhost] => (item=file1)
changed: [localhost] => (item=file2)
failed: [localhost] (item=file3) => {"ansible_loop_var": "item", "changed": true, "cmd": "stat /tmp/file3.txt", "delta": "0:00:00.002938", "end": "2023-02-10 15:03:46.552211", "item": "file3", "msg": "non-zero return code", "rc": 1, "start": "2023-02-10 15:03:46.549273", "stderr": "stat: cannot statx '/tmp/file3.txt': No such file or directory", "stderr_lines": ["stat: cannot statx '/tmp/file3.txt': No such file or directory"], "stdout": "", "stdout_lines": []}
changed: [localhost] => (item=file4)
changed: [localhost] => (item=file5)"""
            self.filename = ""
            self._warn_prefix = False
            self._item_failed = True
            self._item_actioned = False
            self._task_failed = False
            self._task_unreachable = False

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (cb.filename == "failed/a_name")
