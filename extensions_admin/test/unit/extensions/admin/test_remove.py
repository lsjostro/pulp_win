import mock
from pulp.client.commands.unit import UnitRemoveCommand

from ...testbase import PulpClientTests
from pulp_win.extensions.admin import remove as remove_commands
from pulp_win.common.ids import TYPE_ID_MSI, TYPE_ID_MSM
from pulp_win.extensions.admin.remove import (
    BaseRemoveCommand, PackageRemoveCommand)


class BaseRemoveCommandTests(PulpClientTests):
    def setUp(self):
        super(BaseRemoveCommandTests, self).setUp()

        self.command = BaseRemoveCommand(self.context, 'remove')

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UnitRemoveCommand))

    @mock.patch('pulp_win.extensions.admin.units_display.get_formatter_for_type')  # noqa
    def test_get_formatter_for_type(self, mock_display):
        # Setup
        fake_units = 'u'
        fake_task = mock.MagicMock()
        fake_task.result = fake_units

        # Test
        self.command.get_formatter_for_type('foo-type')

        # Verify
        mock_display.assert_called_once_with('foo-type')


class PackageRemoveCommandTests(PulpClientTests):
    """
    Simply verifies the criteria_utils is called from the overridden methods.
    """

    @mock.patch('pulp_win.extensions.admin.criteria_utils.parse_key_value')
    def test_key_value(self, mock_parse):
        command = remove_commands.MsiRemoveCommand(self.context, 'copy')
        command._parse_key_value('foo')
        mock_parse.assert_called_once_with('foo')

    @mock.patch('pulp_win.extensions.admin.criteria_utils.parse_sort')
    def test_sort(self, mock_parse):
        command = remove_commands.MsiRemoveCommand(self.context, 'copy')
        command._parse_sort('foo')
        mock_parse.assert_called_once_with(
            remove_commands.BaseRemoveCommand, 'foo')

    @mock.patch('pulp.client.commands.unit.UnitRemoveCommand.modify_user_input')  # noqa
    def test_modify_user_input(self, mock_super):
        command = remove_commands.MsiRemoveCommand(self.context, 'remove')
        user_input = {'a': 'a'}
        command.modify_user_input(user_input)

        # The super call is required.
        self.assertEqual(1, mock_super.call_count)

        # The user_input variable itself should be modified.
        self.assertEqual(user_input, {'a': 'a'})


class RemoveCommandsTests(PulpClientTests):
    """
    The command implementations are simply configuration to the base commands,
    so rather than re-testing the functionality of the base commands, they
    simply assert that the configuration is correct.
    """

    def test_msi_remove_command(self):
        # Test
        command = remove_commands.MsiRemoveCommand(self.context)

        # Verify
        self.assertTrue(isinstance(command, PackageRemoveCommand))
        self.assertEqual(command.name, TYPE_ID_MSI)
        self.assertEqual(command.description, remove_commands.DESC_MSI)
        self.assertEqual(command.type_id, TYPE_ID_MSI)

    def test_msm_remove_command(self):
        # Test
        command = remove_commands.MsmRemoveCommand(self.context)

        # Verify
        self.assertTrue(isinstance(command, PackageRemoveCommand))
        self.assertEqual(command.name, TYPE_ID_MSM)
        self.assertEqual(command.description, remove_commands.DESC_MSM)
        self.assertEqual(command.type_id, TYPE_ID_MSM)
