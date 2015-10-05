#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import lxml.etree
import mock
import requests_mock

import dracclient.client
from dracclient import exceptions
from dracclient.resources import bios
import dracclient.resources.job
from dracclient.resources import lifecycle_controller
from dracclient.resources import uris
from dracclient.tests import base
from dracclient.tests import utils as test_utils
from dracclient import utils


@requests_mock.Mocker()
class ClientPowerManagementTestCase(base.BaseTest):

    def setUp(self):
        super(ClientPowerManagementTestCase, self).setUp()
        self.drac_client = dracclient.client.DRACClient(
            **test_utils.FAKE_ENDPOINT)

    def test_get_power_state(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSEnumerations[uris.DCIM_ComputerSystem]['ok'])

        self.assertEqual('POWER_ON', self.drac_client.get_power_state())

    def test_set_power_state(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSInvocations[
                uris.DCIM_ComputerSystem]['RequestStateChange']['ok'])

        self.assertIsNone(self.drac_client.set_power_state('POWER_ON'))

    def test_set_power_state_fail(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSInvocations[
                uris.DCIM_ComputerSystem]['RequestStateChange']['error'])

        self.assertRaises(exceptions.DRACOperationFailed,
                          self.drac_client.set_power_state, 'POWER_ON')

    def test_set_power_state_invalid_target_state(self, mock_requests):
        self.assertRaises(exceptions.InvalidParameterValue,
                          self.drac_client.set_power_state, 'foo')


class ClientBootManagementTestCase(base.BaseTest):

    def setUp(self):
        super(ClientBootManagementTestCase, self).setUp()
        self.drac_client = dracclient.client.DRACClient(
            **test_utils.FAKE_ENDPOINT)

    @requests_mock.Mocker()
    def test_list_boot_modes(self, mock_requests):
        expected_boot_mode = bios.BootMode(id='IPL', name='BootSeq',
                                           is_current=True, is_next=True)
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSEnumerations[
                uris.DCIM_BootConfigSetting]['ok'])

        boot_modes = self.drac_client.list_boot_modes()

        self.assertEqual(5, len(boot_modes))
        self.assertIn(expected_boot_mode, boot_modes)

    @requests_mock.Mocker()
    def test_list_boot_devices(self, mock_requests):
        expected_boot_device = bios.BootDevice(
            id=('IPL:BIOS.Setup.1-1#BootSeq#NIC.Embedded.1-1-1#'
                'fbeeb18f19fd4e768c941e66af4fc424'),
            boot_mode='IPL',
            pending_assigned_sequence=0,
            current_assigned_sequence=0,
            bios_boot_string=('Embedded NIC 1 Port 1 Partition 1: '
                              'BRCM MBA Slot 0200 v16.4.3 BootSeq'))
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSEnumerations[
                uris.DCIM_BootSourceSetting]['ok'])

        boot_devices = self.drac_client.list_boot_devices()

        self.assertEqual(3, len(boot_devices))
        self.assertIn('IPL', boot_devices)
        self.assertIn('BCV', boot_devices)
        self.assertIn('UEFI', boot_devices)
        self.assertEqual(3, len(boot_devices['IPL']))
        self.assertIn(expected_boot_device, boot_devices['IPL'])
        self.assertEqual(
            0,  boot_devices['IPL'][0].pending_assigned_sequence)
        self.assertEqual(
            1,  boot_devices['IPL'][1].pending_assigned_sequence)
        self.assertEqual(
            2,  boot_devices['IPL'][2].pending_assigned_sequence)

    @requests_mock.Mocker()
    @mock.patch.object(lifecycle_controller.LifecycleControllerManagement,
                       'get_version', spec_set=True, autospec=True)
    def test_list_boot_devices_11g(self, mock_requests,
                                   mock_get_lifecycle_controller_version):
        expected_boot_device = bios.BootDevice(
            id=('IPL:NIC.Embedded.1-1:082927b7c62a9f52ef0d65a33416d76c'),
            boot_mode='IPL',
            pending_assigned_sequence=0,
            current_assigned_sequence=0,
            bios_boot_string=('Embedded NIC 1: '
                              'BRCM MBA Slot 0200 v7.2.3 BootSeq'))

        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSEnumerations[
                uris.DCIM_BootSourceSetting]['ok-11g'])
        mock_get_lifecycle_controller_version.return_value = (1, 0, 0)

        boot_devices = self.drac_client.list_boot_devices()

        self.assertEqual(3, len(boot_devices))
        self.assertIn('IPL', boot_devices)
        self.assertIn('BCV', boot_devices)
        self.assertIn('UEFI', boot_devices)
        self.assertEqual(3, len(boot_devices['IPL']))
        self.assertIn(expected_boot_device, boot_devices['IPL'])
        self.assertEqual(
            0,  boot_devices['IPL'][0].pending_assigned_sequence)
        self.assertEqual(
            1,  boot_devices['IPL'][1].pending_assigned_sequence)
        self.assertEqual(
            2,  boot_devices['IPL'][2].pending_assigned_sequence)

    @requests_mock.Mocker()
    def test_change_boot_device_order(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSInvocations[
                uris.DCIM_BootConfigSetting][
                    'ChangeBootOrderByInstanceID']['ok'])

        self.assertIsNone(
            self.drac_client.change_boot_device_order('IPL', 'foo'))

    @mock.patch.object(dracclient.client.WSManClient, 'invoke',
                       spec_set=True, autospec=True)
    def test_change_boot_device_order_list(self, mock_invoke):
        expected_selectors = {'InstanceID': 'IPL'}
        expected_properties = {'source': ['foo', 'bar', 'baz']}
        mock_invoke.return_value = lxml.etree.fromstring(
            test_utils.BIOSInvocations[uris.DCIM_BootConfigSetting][
                'ChangeBootOrderByInstanceID']['ok'])

        self.drac_client.change_boot_device_order('IPL',
                                                  ['foo', 'bar', 'baz'])

        mock_invoke.assert_called_once_with(
            mock.ANY, uris.DCIM_BootConfigSetting,
            'ChangeBootOrderByInstanceID', expected_selectors,
            expected_properties, expected_return_value=utils.RET_SUCCESS)

    @requests_mock.Mocker()
    def test_change_boot_device_order_error(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.BIOSInvocations[
                uris.DCIM_BootConfigSetting][
                    'ChangeBootOrderByInstanceID']['error'])

        self.assertRaises(
            exceptions.DRACOperationFailed,
            self.drac_client.change_boot_device_order, 'IPL', 'foo')


class ClientJobManagementTestCase(base.BaseTest):

    def setUp(self):
        super(ClientJobManagementTestCase, self).setUp()
        self.drac_client = dracclient.client.DRACClient(
            **test_utils.FAKE_ENDPOINT)

    @requests_mock.Mocker()
    def test_list_jobs(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.JobEnumerations[uris.DCIM_LifecycleJob]['ok'])

        jobs = self.drac_client.list_jobs()

        self.assertEqual(6, len(jobs))

    @mock.patch.object(dracclient.client.WSManClient, 'enumerate',
                       spec_set=True, autospec=True)
    def test_list_jobs_only_unfinished(self, mock_enumerate):
        expected_filter_query = ('select * from DCIM_LifecycleJob '
                                 'where Name != "CLEARALL" and '
                                 'JobStatus != "Reboot Completed" and '
                                 'JobStatus != "Completed" and '
                                 'JobStatus != "Completed with Errors" and '
                                 'JobStatus != "Failed"')
        mock_enumerate.return_value = lxml.etree.fromstring(
            test_utils.JobEnumerations[uris.DCIM_LifecycleJob]['ok'])

        self.drac_client.list_jobs(only_unfinished=True)

        mock_enumerate.assert_called_once_with(
            mock.ANY, uris.DCIM_LifecycleJob,
            filter_query=expected_filter_query)

    @mock.patch.object(dracclient.client.WSManClient, 'enumerate',
                       spec_set=True, autospec=True)
    def test_get_job(self, mock_enumerate):
        expected_filter_query = ('select * from DCIM_LifecycleJob'
                                 ' where InstanceID="42"')
        # NOTE: This is the first job in the xml. Filtering the job is the
        #       responsibility of the controller, so not testing it.
        expected_job = dracclient.resources.job.Job(id='JID_CLEARALL',
                                                    name='CLEARALL',
                                                    start_time='TIME_NA',
                                                    until_time='TIME_NA',
                                                    message='NA',
                                                    state='Pending',
                                                    percent_complete='0')
        mock_enumerate.return_value = lxml.etree.fromstring(
            test_utils.JobEnumerations[uris.DCIM_LifecycleJob]['ok'])

        job = self.drac_client.get_job(42)

        mock_enumerate.assert_called_once_with(
            mock.ANY, uris.DCIM_LifecycleJob,
            filter_query=expected_filter_query)
        self.assertEqual(expected_job, job)

    @mock.patch.object(dracclient.client.WSManClient, 'enumerate',
                       spec_set=True, autospec=True)
    def test_get_job_not_found(self, mock_enumerate):
        expected_filter_query = ('select * from DCIM_LifecycleJob'
                                 ' where InstanceID="42"')
        mock_enumerate.return_value = lxml.etree.fromstring(
            test_utils.JobEnumerations[uris.DCIM_LifecycleJob]['not_found'])

        job = self.drac_client.get_job(42)

        mock_enumerate.assert_called_once_with(
            mock.ANY, uris.DCIM_LifecycleJob,
            filter_query=expected_filter_query)
        self.assertIsNone(job)

    @mock.patch.object(dracclient.client.WSManClient, 'invoke',
                       spec_set=True, autospec=True)
    def test_create_config_job(self, mock_invoke):
        cim_creation_class_name = 'DCIM_BIOSService'
        cim_name = 'DCIM:BIOSService'
        target = 'BIOS.Setup.1-1'
        expected_selectors = {'CreationClassName': cim_creation_class_name,
                              'Name': cim_name,
                              'SystemCreationClassName': 'DCIM_ComputerSystem',
                              'SystemName': 'DCIM:ComputerSystem'}
        expected_properties = {'Target': target,
                               'ScheduledStartTime': 'TIME_NOW'}
        mock_invoke.return_value = lxml.etree.fromstring(
            test_utils.JobInvocations[uris.DCIM_BIOSService][
                'CreateTargetedConfigJob']['ok'])

        job_id = self.drac_client.create_config_job(
            uris.DCIM_BIOSService, cim_creation_class_name, cim_name, target)

        mock_invoke.assert_called_once_with(
            mock.ANY, uris.DCIM_BIOSService, 'CreateTargetedConfigJob',
            expected_selectors, expected_properties,
            expected_return_value=utils.RET_CREATED)
        self.assertEqual('JID_442507917525', job_id)

    @requests_mock.Mocker()
    def test_create_config_job_failed(self, mock_requests):
        cim_creation_class_name = 'DCIM_BIOSService'
        cim_name = 'DCIM:BIOSService'
        target = 'BIOS.Setup.1-1'
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.JobInvocations[uris.DCIM_BIOSService][
                'CreateTargetedConfigJob']['error'])

        self.assertRaises(
            exceptions.DRACOperationFailed, self.drac_client.create_config_job,
            uris.DCIM_BIOSService, cim_creation_class_name, cim_name, target)

    @mock.patch.object(dracclient.client.WSManClient, 'invoke', spec_set=True,
                       autospec=True)
    def test_create_config_job_with_reboot(self, mock_invoke):
        cim_creation_class_name = 'DCIM_BIOSService'
        cim_name = 'DCIM:BIOSService'
        target = 'BIOS.Setup.1-1'
        expected_selectors = {'CreationClassName': cim_creation_class_name,
                              'Name': cim_name,
                              'SystemCreationClassName': 'DCIM_ComputerSystem',
                              'SystemName': 'DCIM:ComputerSystem'}
        expected_properties = {'Target': target,
                               'RebootJobType': '3',
                               'ScheduledStartTime': 'TIME_NOW'}
        mock_invoke.return_value = lxml.etree.fromstring(
            test_utils.JobInvocations[uris.DCIM_BIOSService][
                'CreateTargetedConfigJob']['ok'])

        job_id = self.drac_client.create_config_job(
            uris.DCIM_BIOSService, cim_creation_class_name, cim_name, target,
            reboot=True)

        mock_invoke.assert_called_once_with(
            mock.ANY, uris.DCIM_BIOSService, 'CreateTargetedConfigJob',
            expected_selectors, expected_properties,
            expected_return_value=utils.RET_CREATED)
        self.assertEqual('JID_442507917525', job_id)

    @mock.patch.object(dracclient.client.WSManClient, 'invoke', spec_set=True,
                       autospec=True)
    def test_delete_pending_config(self, mock_invoke):
        cim_creation_class_name = 'DCIM_BIOSService'
        cim_name = 'DCIM:BIOSService'
        target = 'BIOS.Setup.1-1'
        expected_selectors = {'CreationClassName': cim_creation_class_name,
                              'Name': cim_name,
                              'SystemCreationClassName': 'DCIM_ComputerSystem',
                              'SystemName': 'DCIM:ComputerSystem'}
        expected_properties = {'Target': target}
        mock_invoke.return_value = lxml.etree.fromstring(
            test_utils.JobInvocations[uris.DCIM_BIOSService][
                'DeletePendingConfiguration']['ok'])

        self.drac_client.delete_pending_config(
            uris.DCIM_BIOSService, cim_creation_class_name, cim_name, target)

        mock_invoke.assert_called_once_with(
            mock.ANY, uris.DCIM_BIOSService, 'DeletePendingConfiguration',
            expected_selectors, expected_properties,
            expected_return_value=utils.RET_SUCCESS)

    @requests_mock.Mocker()
    def test_delete_pending_config_failed(self, mock_requests):
        cim_creation_class_name = 'DCIM_BIOSService'
        cim_name = 'DCIM:BIOSService'
        target = 'BIOS.Setup.1-1'
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.JobInvocations[uris.DCIM_BIOSService][
                'DeletePendingConfiguration']['error'])

        self.assertRaises(
            exceptions.DRACOperationFailed,
            self.drac_client.delete_pending_config, uris.DCIM_BIOSService,
            cim_creation_class_name, cim_name, target)


class ClientBIOSChangesTestCase(base.BaseTest):

    def setUp(self):
        super(ClientBIOSChangesTestCase, self).setUp()
        self.drac_client = dracclient.client.DRACClient(
            **test_utils.FAKE_ENDPOINT)

    @mock.patch.object(dracclient.resources.job.JobManagement,
                       'create_config_job', spec_set=True, autospec=True)
    def test_commit_pending_bios_changes(self, mock_create_config_job):
        self.drac_client.commit_pending_bios_changes()

        mock_create_config_job.assert_called_once_with(
            mock.ANY, resource_uri=uris.DCIM_BIOSService,
            cim_creation_class_name='DCIM_BIOSService',
            cim_name='DCIM:BIOSService', target='BIOS.Setup.1-1')

    @mock.patch.object(dracclient.resources.job.JobManagement,
                       'delete_pending_config', spec_set=True, autospec=True)
    def test_abandon_pending_bios_changes(self, mock_delete_pending_config):
        self.drac_client.abandon_pending_bios_changes()

        mock_delete_pending_config.assert_called_once_with(
            mock.ANY, resource_uri=uris.DCIM_BIOSService,
            cim_creation_class_name='DCIM_BIOSService',
            cim_name='DCIM:BIOSService', target='BIOS.Setup.1-1')


class ClientLifecycleControllerManagementTestCase(base.BaseTest):

    def setUp(self):
        super(ClientLifecycleControllerManagementTestCase, self).setUp()
        self.drac_client = dracclient.client.DRACClient(
            **test_utils.FAKE_ENDPOINT)

    @requests_mock.Mocker()
    def test_get_lifecycle_controller_version(self, mock_requests):
        mock_requests.post(
            'https://1.2.3.4:443/wsman',
            text=test_utils.LifecycleControllerEnumerations[
                uris.DCIM_SystemView]['ok'])

        version = self.drac_client.get_lifecycle_controller_version()

        self.assertEqual((2, 1, 0), version)


@requests_mock.Mocker()
class WSManClientTestCase(base.BaseTest):

    def test_enumerate(self, mock_requests):
        mock_requests.post('https://1.2.3.4:443/wsman',
                           text='<result>yay!</result>')

        client = dracclient.client.WSManClient(**test_utils.FAKE_ENDPOINT)
        resp = client.enumerate('http://resource')
        self.assertEqual('yay!', resp.text)

    def test_invoke(self, mock_requests):
        xml = """
<response xmlns:n1="http://resource">
    <n1:ReturnValue>42</n1:ReturnValue>
    <result>yay!</result>
</response>
"""  # noqa
        mock_requests.post('https://1.2.3.4:443/wsman', text=xml)

        client = dracclient.client.WSManClient(**test_utils.FAKE_ENDPOINT)
        resp = client.invoke('http://resource', 'Foo')
        self.assertEqual('yay!', resp.find('result').text)

    def test_invoke_with_expected_return_value(self, mock_requests):
        xml = """
<response xmlns:n1="http://resource">
    <n1:ReturnValue>42</n1:ReturnValue>
    <result>yay!</result>
</response>
"""  # noqa
        mock_requests.post('https://1.2.3.4:443/wsman', text=xml)

        client = dracclient.client.WSManClient(**test_utils.FAKE_ENDPOINT)
        resp = client.invoke('http://resource', 'Foo',
                             expected_return_value='42')
        self.assertEqual('yay!', resp.find('result').text)

    def test_invoke_with_error_return_value(self, mock_requests):
        xml = """
<response xmlns:n1="http://resource">
    <n1:ReturnValue>2</n1:ReturnValue>
    <result>yay!</result>
</response>
"""  # noqa
        mock_requests.post('https://1.2.3.4:443/wsman', text=xml)

        client = dracclient.client.WSManClient(**test_utils.FAKE_ENDPOINT)
        self.assertRaises(exceptions.DRACOperationFailed, client.invoke,
                          'http://resource', 'Foo')

    def test_invoke_with_unexpected_return_value(self, mock_requests):
        xml = """
<response xmlns:n1="http://resource">
    <n1:ReturnValue>42</n1:ReturnValue>
    <result>yay!</result>
</response>
"""  # noqa
        mock_requests.post('https://1.2.3.4:443/wsman', text=xml)

        client = dracclient.client.WSManClient(**test_utils.FAKE_ENDPOINT)
        self.assertRaises(exceptions.DRACUnexpectedReturnValue, client.invoke,
                          'http://resource', 'Foo',
                          expected_return_value='4242')