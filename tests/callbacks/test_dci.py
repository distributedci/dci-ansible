import os

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

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (cb.filename == "failed/a_name")


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

        def create_file(self, name, content):
            self.filename = name

    cb = MyCallback()
    cb.banner("a message")

    assert (cb.filename == "failed/a_name")


def test_redact_disabled():
    """Test that redact can be completely disabled."""
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'False'
    cb = CallbackModule()
    content = "password=secret123 ghp_1234567890123456789012345678901234"
    assert cb._redact_content(content) == content


def test_redact_github_personal_token():
    """Test GitHub personal access token redact."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    # GitHub PAT: ghp_ + 36 characters (40 total)
    token = "ghp_" + "1234567890" * 3 + "123456"  # exactly 36 chars after prefix
    content = f"Using token: {token} for auth"
    result = cb._redact_content(content)
    assert token not in result
    assert '*******' in result
    assert 'Using token:' in result


def test_redact_github_finegrained_token():
    """Test GitHub fine-grained PAT redact."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    content = "github_pat_" + "A" * 82
    result = cb._redact_content(content)
    assert 'github_pat_' not in result
    assert '*******' in result


def test_redact_dci_remoteci_id():
    """Test DCI remoteci ID redact."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    content = "remoteci/12345678-1234-1234-1234-123456789abc is configured"
    result = cb._redact_content(content)
    assert 'remoteci/12345678-1234-1234-1234-123456789abc' not in result
    assert '*******' in result


def test_redact_dci_remoteci_secret_old():
    """Test DCI remoteci secret (old 64-char format) redact."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    secret = "A" * 64
    content = f"secret: {secret}"
    result = cb._redact_content(content)
    assert secret not in result
    assert '*******' in result


def test_redact_dci_remoteci_secret_new():
    """Test DCI remoteci secret (new DCI. format) redact."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    secret = "DCI." + "B" * 60
    content = f"api_secret: {secret}"
    result = cb._redact_content(content)
    assert secret not in result
    assert '*******' in result


def test_redact_pull_secret_json():
    """Test pull secret redact in JSON format."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    content = '{"auths": {"registry": {"auth": "cHJlZ2ErcHJlZ2E6base64data"}}}'
    result = cb._redact_content(content)
    assert 'cHJlZ2ErcHJlZ2E6base64data' not in result
    assert '"auth": "*******"' in result
    assert '{"auths":' in result  # Structure preserved


def test_redact_pull_secret_yaml():
    """Test pull secret redact in YAML format."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    content = """auths:
  registry:
    auth: cHJlZ2ErcHJlZ2E6base64data
    email: user@example.com"""
    result = cb._redact_content(content)
    assert 'cHJlZ2ErcHJlZ2E6base64data' not in result
    assert 'auth: *******' in result
    assert 'email: user@example.com' in result  # Other fields preserved


def test_redact_custom_pattern():
    """Test custom user-specified pattern."""

    os.environ.clear()
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT_PATTERNS'] = r'mytoken=\S+'
    cb = CallbackModule()
    content = "config: mytoken=abc123xyz"
    result = cb._redact_content(content)
    assert 'mytoken=abc123xyz' not in result
    assert '*******' in result
    os.environ.clear()


def test_redact_multiple_patterns():
    """Test multiple custom patterns separated by colon."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT_PATTERNS'] = r'password=\S+:token=\S+'
    cb = CallbackModule()
    content = "credentials: password=secret123 token=abc456"
    result = cb._redact_content(content)
    assert 'secret123' not in result
    assert 'abc456' not in result
    assert result.count('*******') == 2
    os.environ.clear()


def test_redact_invalid_pattern():
    """Test handling of invalid regex pattern."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT_PATTERNS'] = '[invalid(regex'
    cb = CallbackModule()
    # Should not raise exception, pattern list should be empty
    assert len(cb._redact_patterns) == 0
    # Content should be unchanged
    content = "test content"
    assert cb._redact_content(content) == content
    os.environ.clear()


def test_redact_bytes_content():
    """Test redact works with bytes content."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    # GitHub PAT: ghp_ + 36 characters
    token = "ghp_" + "1234567890" * 3 + "123456"
    content = f"token: {token}".encode()
    result = cb._redact_content(content)
    assert isinstance(result, bytes)
    assert token.encode() not in result
    assert b'*******' in result


def test_redact_none_content():
    """Test redact gracefully handles None content."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    assert cb._redact_content(None) is None


def test_redact_empty_content():
    """Test redact handles empty string and bytes."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    assert cb._redact_content('') == ''
    assert cb._redact_content(b'') == b''


def test_redact_multiline():
    """Test redact works across multiple lines."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    cb = CallbackModule()
    # GitHub PAT: ghp_ + 36 characters
    token = "ghp_" + "1234567890" * 3 + "123456"
    content = f"""line1
token: {token}
line3
remoteci/12345678-1234-1234-1234-123456789abc
line5"""
    result = cb._redact_content(content)
    assert token not in result
    assert 'remoteci/12345678-1234-1234-1234-123456789abc' not in result
    assert result.count('*******') == 2
    assert 'line1' in result
    assert 'line3' in result
    assert 'line5' in result


def test_redact_defaults_disabled():
    """Test that default patterns are disabled when custom patterns are specified."""

    os.environ['ANSIBLE_CALLBACK_DCI_REDACT'] = 'True'
    # When custom patterns are specified, defaults are NOT used
    os.environ['ANSIBLE_CALLBACK_DCI_REDACT_PATTERNS'] = r'custompattern_\w+'
    cb = CallbackModule()
    content = "ghp_1234567890123456789012345678901234"
    # GitHub token should NOT be redacted (only custom pattern is active)
    result = cb._redact_content(content)
    assert result == content
    os.environ.clear()
