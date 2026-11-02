from unittest import mock

from callback.dci import CallbackModule
from ansible import constants as C
from ansible.plugins.callback.default import CallbackModule as CM_default


def make_cb(**attrs):
    """A CallbackModule with banner() inputs set, capturing the name passed to
    create_file instead of uploading it."""
    cb = CallbackModule()
    cb._name = "a_name"
    cb._content = "content"
    cb._color = None
    cb._warn_prefix = False
    cb._item_failed = False
    cb._item_actioned = False
    cb._task_failed = False
    cb._task_unreachable = False
    cb._task_ignored = False
    for key, val in attrs.items():
        setattr(cb, key, val)
    cb.filename = None
    cb.create_file = lambda name, content: setattr(cb, "filename", name)
    return cb


def test_banner_success():
    cb = CallbackModule()
    cb.banner("a message")

    assert cb._name == "a message"


def test_banner_error():
    cb = make_cb(_color=C.COLOR_ERROR)
    cb.banner("next")

    assert cb.filename == "failed/a_name"


def test_banner_error_then_include():
    """A failed task followed by an 'included:' line (COLOR_SKIP) must still be
    recorded as failed/, even though the last color seen is not COLOR_ERROR.
    Reproduces a failing 'include_tasks' whose failure was hidden."""
    cb = make_cb(_color=C.COLOR_SKIP, _item_actioned=True, _task_failed=True)
    cb.banner("next")

    assert cb.filename == "failed/a_name"


def test_banner_error_loop():
    """A non-ignored loop with a failed item is recorded as failed/."""
    cb = make_cb(_color=C.COLOR_CHANGED, _item_failed=True)
    cb.banner("next")

    assert cb.filename == "failed/a_name"


def test_banner_unreachable():
    cb = make_cb(_task_unreachable=True)
    cb.banner("next")

    assert cb.filename == "unreachable/a_name"


def test_banner_ignored():
    """ignore_errors / ignore_unreachable: Ansible reports the task as
    'ignored', so it gets the ignored/ prefix (not failed/unreachable)."""
    cb = make_cb(_color=C.COLOR_SKIP, _task_ignored=True)
    cb.banner("next")

    assert cb.filename == "ignored/a_name"


def test_banner_ignored_wins_over_failed_item():
    """An ignored loop still has a failed item (_item_failed), but the task as a
    whole was ignored, so it must be ignored/, not failed/."""
    cb = make_cb(_color=C.COLOR_SKIP, _item_failed=True, _item_actioned=True,
                 _task_ignored=True)
    cb.banner("next")

    assert cb.filename == "ignored/a_name"


def test_on_failed_ignored_sets_ignored():
    """ignore_errors failure -> _task_ignored, never _task_failed, regardless of
    a failed loop item."""
    cb = CallbackModule()
    cb._item_failed = True
    with mock.patch.object(CM_default, "v2_runner_on_failed"):
        cb.v2_runner_on_failed(mock.Mock(), ignore_errors=True)
    assert cb._task_ignored is True
    assert cb._task_failed is False


def test_on_failed_not_ignored_sets_failed():
    """A real (non-ignored) failure -- including a rescued block task, which
    arrives with ignore_errors=False -- sets _task_failed."""
    cb = CallbackModule()
    with mock.patch.object(CM_default, "v2_runner_on_failed"):
        cb.v2_runner_on_failed(mock.Mock(), ignore_errors=False)
    assert cb._task_failed is True
    assert cb._task_ignored is False


def test_on_unreachable_sets_unreachable():
    cb = CallbackModule()
    result = mock.Mock()
    result._task.ignore_unreachable = False
    with mock.patch.object(CM_default, "v2_runner_on_unreachable"):
        cb.v2_runner_on_unreachable(result)
    assert cb._task_unreachable is True
    assert cb._task_ignored is False


def test_on_unreachable_ignored_sets_ignored():
    """ignore_unreachable -> Ansible reports 'ignored', not 'unreachable'."""
    cb = CallbackModule()
    result = mock.Mock()
    result._task.ignore_unreachable = True
    with mock.patch.object(CM_default, "v2_runner_on_unreachable"):
        cb.v2_runner_on_unreachable(result)
    assert cb._task_ignored is True
    assert cb._task_unreachable is False
