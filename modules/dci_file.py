# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ansible.module_utils.basic import *
from ansible.module_utils.dci_common import *
from ansible.module_utils.dci_base import *
import os

try:
    from dciclient.v1.api import file as dci_file
    from dciclient.v1.api import redact as dci_redact
except ImportError:
    dciclient_found = False
else:
    dciclient_found = True


DOCUMENTATION = '''
---
module: dci_file
short_description: module to interact with the files endpoint of DCI
description:
  - DCI module to manage the file resources
version_added: 2.2
options:
  state:
    required: false
    description: Desired state of the resource
  dci_login:
    required: false
    description: User's DCI login
  dci_password:
    required: false
    description: User's DCI password
  dci_cs_url:
    required: false
    description: DCI Control Server URL
  job_id:
    required: false
    description: ID of the job to attach the file to
  jobstate_id:
    required: false
    description: ID of the jobstate to attach the file to
  mime:
    required: false
    default: text/plain
    description: mime-type of the document to upload
  path:
    required: true
    description: Path of the document to upload
  name:
    required: false
    description: Name under which the file will be saved on the control-server
  content:
    required: false
    description: Content of the file to upload
  max_size:
    required: false
    default: 256
    description: Maximum file size in MB. Files exceeding this limit will be rejected before upload.
  redact:
    required: false
    default: true
    description: Redact sensitive data (tokens, credentials, pull secrets) before uploading. Can be overridden globally with the DCI_REDACT environment variable.
  embed:
    required: false
    description:
      - List of field to embed within the retrieved resource
  query:
    required: false
    description: query language
'''

EXAMPLES = '''
- name: Attach files to job
  dci_file:
    job_id: '{{ job_id }}'
    path: '{{ item.path }}'
    name: '{{ item.name }}'
  with_items:
    - {'name': 'SSHd config', 'path': '/etc/ssh/sshd_config'}
    - {'name': 'My OpenStack config', 'path': '/etc/myown.conf'}


- name: Get file information
  dci_file:
    id: XXXXX


- name: Attach content to a file to a job
  dci_file:
    job_id: '{{ job_id }}'
    content: 'This is the content of the file I want to create'
    name: 'My test file'


- name: Remove file
  dci_file:
    state: absent
    id: XXXXX


- name: Attach junit result
  dci_file:
    path: '{{ item }}'
    job_id: '{{ job_id }}'
    mime: 'application/junit'
  with_items:
    - '/tmp/result.xml'
'''

# TODO
RETURN = '''
'''


def _is_bin_file(path):
    """Return True when the file contains a NUL byte.

    A NUL-byte does not occur in text, its presence flags a binary file.
    """
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                if b"\x00" in chunk:
                    return True
    except OSError:
        return False
    return False


class DciFile(DciBase):

    def __init__(self, params):
        super(DciFile, self).__init__(dci_file)
        self.id = params.get('id')
        self.content = params.get('content')
        self.path = params.get('path')
        self.file_path = params.get('path')
        self.name = params.get('name')
        self.job_id = params.get('job_id')
        self.jobstate_id = params.get('jobstate_id')
        self.mime = params.get('mime')
        self.max_size = params.get('max_size')
        self.redact = params.get('redact')
        self.search_criterias = {
            'embed': params.get('embed'),
            'where': params.get('where'),
            'query': params.get('query')
        }
        self.deterministic_params = ['name', 'mime', 'file_path', 'content',
                                     'job_id', 'jobstate_id']

    def do_create(self, context):
        if not self.job_id and not self.jobstate_id:
            raise DciParameterError(
                'Either job_id or jobstate_id must be specified')
        if not self.content and not self.path:
            raise DciParameterError(
                'Either content or path must be specified')
        if self.content and not self.name:
            raise DciParameterError(
                'name parameter must be specified ',
                'when content has been specified')

        if self.path and not self.name:
            self.name = self.path

        if self.path and not os.path.exists(self.path):
            raise DciParameterError('%s: No such file' % self.path)

        if self.path and self.max_size:
            file_size = os.path.getsize(self.path)
            max_size_bytes = self.max_size * 1024 * 1024
            if file_size > max_size_bytes:
                raise DciParameterError(
                    '%s: file too large (%d MB > %d MB limit)' % (
                        self.path,
                        file_size // (1024 * 1024),
                        self.max_size))
        redacted_path = None
        if dci_redact.should_redact(self.redact):
            if self.content:
                self.content = dci_redact.redact_content(self.content)
            elif self.path and not _is_bin_file(self.path):
                dir_name = os.path.dirname(self.path)
                base_name = os.path.basename(self.path)
                redacted_path = os.path.join(dir_name, ".%s.redacted" % base_name)
                dci_redact.redact_file(self.path, redacted_path)
                self.path = redacted_path
                self.file_path = redacted_path

        try:
            return super(DciFile, self).do_create(context)
        finally:
            if redacted_path and os.path.exists(redacted_path):
                os.remove(redacted_path)

    def do_delete(self, context):
        return self.resource.delete(context, self.id)


def main():

    resource_argument_spec = dict(
        state=dict(default='present',
                   choices=['present', 'absent'],
                   type='str'),
        id=dict(type='str'),
        content=dict(type='str'),
        path=dict(type='str'),
        name=dict(type='str'),
        job_id=dict(type='str'),
        jobstate_id=dict(type='str'),
        mime=dict(default='text/plain', type='str'),
        max_size=dict(default=256, type='int'),
        redact=dict(default=True, type='bool'),
        embed=dict(type='str'),
        where=dict(type='str'),
        query=dict(type='str')
    )
    resource_argument_spec.update(authentication_argument_spec())

    module = AnsibleModule(
        argument_spec=resource_argument_spec,
        required_if=[['state', 'absent', ['id']]],
        mutually_exclusive=[['content', 'path']],
    )

    if not dciclient_found:
        module.fail_json(msg='The python dciclient module is required')

    context = build_dci_context(module)
    action_name = get_standard_action(module.params)

    l_file = DciFile(module.params)
    action_func = getattr(l_file, 'do_%s' % action_name)

    http_response = run_action_func(action_func, context, module)
    result = parse_http_response(http_response, dci_file, context, module)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
